/*
 * python-wrapper.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */


#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <libxml/xmlversion.h>

#include "../gumbo/gumbo.h"
#include "as-libxml.h"

#define MAJOR 0
#define MINOR 2
#define PATCH 1

static char *NAME =  "libxml2:xmlDoc";
static char *DESTRUCTOR = "destructor:xmlFreeDoc";

static inline xmlNodePtr
py_convert_tree(xmlDocPtr doc, GumboNode *root, Options *opts) {
    char *errmsg = NULL;
    xmlNodePtr ans;

    Py_BEGIN_ALLOW_THREADS;
    ans = convert_tree(doc, root, opts, &errmsg);
    Py_END_ALLOW_THREADS;
    if (ans == NULL) {
        if (errmsg) PyErr_SetString(PyExc_Exception, errmsg);
        else PyErr_NoMemory();
    }
    return ans;
}

static inline bool 
parse_with_options(xmlDocPtr doc, const char* buffer, size_t buffer_length, Options *opts) {
    GumboOutput *output = NULL;
    xmlNodePtr root = NULL;
    Py_BEGIN_ALLOW_THREADS;
    output = gumbo_parse_with_options(&(opts->gumbo_opts), buffer, buffer_length);
    Py_END_ALLOW_THREADS;
    if (output == NULL) { PyErr_NoMemory(); return false; }
    if (opts->keep_doctype) {
        GumboDocument* doctype = & output->document->v.document;
        if(!xmlCreateIntSubset(
                doc,
                BAD_CAST doctype->name,
                BAD_CAST doctype->public_identifier,
                BAD_CAST doctype->system_identifier)) {
            PyErr_NoMemory();
            gumbo_destroy_output(output);
            return false;
        }
    }
    root = py_convert_tree(doc, output->root, opts);
    if (root) xmlDocSetRootElement(doc, root);
    gumbo_destroy_output(output);
    return root ? true : false;
}

static void 
free_encapsulated_doc(PyObject *capsule) {
    xmlDocPtr doc = PyCapsule_GetPointer(capsule, NAME);
    if (doc != NULL) {
        char *ctx = PyCapsule_GetContext(capsule);
        if (ctx == DESTRUCTOR) xmlFreeDoc(doc);
    }
}

static inline PyObject*
encapsulate(xmlDocPtr doc) {
    PyObject *ans = NULL;
    ans = PyCapsule_New(doc, NAME, free_encapsulated_doc);
    if (ans == NULL) { xmlFreeDoc(doc); return NULL; }
    if (PyCapsule_SetContext(ans, DESTRUCTOR) != 0) { Py_DECREF(ans); return NULL; }
    return ans;
}

static PyObject *
parse(PyObject UNUSED *self, PyObject *args, PyObject *kwds) {
    xmlDocPtr doc = NULL;
    const char *buffer = NULL;
    Py_ssize_t sz = 0;
    Options opts = {0};
    opts.stack_size = 16 * 1024;
    PyObject *kd = Py_True, *mx = Py_False, *ne = Py_False;
    opts.gumbo_opts = kGumboDefaultOptions;
    opts.gumbo_opts.max_errors = 0;  // We discard errors since we are not reporting them anyway

    static char *kwlist[] = {"data", "namespace_elements", "keep_doctype", "maybe_xhtml", "stack_size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s#|OOOI", kwlist, &buffer, &sz, &ne, &kd, &mx, &(opts.stack_size))) return NULL;
    opts.namespace_elements = PyObject_IsTrue(ne);
    opts.keep_doctype = PyObject_IsTrue(kd);
    opts.gumbo_opts.use_xhtml_rules = PyObject_IsTrue(mx);

    doc = create_doc();
    if (!doc) return PyErr_NoMemory();

    if (!parse_with_options(doc, buffer, (size_t)sz, &opts)) { xmlFreeDoc(doc); return NULL; }
    return encapsulate(doc);
}

static PyObject *
clone_doc(PyObject UNUSED *self, PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) { PyErr_SetString(PyExc_TypeError, "Must specify a capsule as the argument"); return NULL; }
    xmlDocPtr sdoc = PyCapsule_GetPointer(capsule, PyCapsule_GetName(capsule)), doc;
    if (sdoc == NULL) return NULL;
    doc = xmlCopyDoc(sdoc, 1);
    if (doc == NULL) return PyErr_NoMemory();
    return encapsulate(doc);
}

static PyMethodDef 
methods[] = {
    {"parse", (PyCFunction)parse, METH_VARARGS | METH_KEYWORDS,
        "parse()\n\nParse specified bytestring which must be in the UTF-8 encoding."
    },

    {"clone_doc", clone_doc, METH_O,
        "clone_doc()\n\nClone the specified document. Which must be a document returned by the parse() function."
    },

    {NULL, NULL, 0, NULL}
};

#define MODULE_NAME "html_parser"
#define MODULE_DOC "HTML parser in C for speed."

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef 
moduledef = {
        PyModuleDef_HEAD_INIT,
        MODULE_NAME,
        MODULE_DOC,
        0,
        methods,
        NULL,
        NULL,
        NULL,
        NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC
PyInit_html_parser(void) {

#else
#define INITERROR return
PyMODINIT_FUNC
inithtml_parser(void) {
#endif
    PyObject *m;
#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule3(MODULE_NAME, methods, MODULE_DOC);
#endif
    if (m == NULL) INITERROR;
    if (PyModule_AddIntMacro(m, MAJOR) != 0) INITERROR;
    if (PyModule_AddIntMacro(m, MINOR) != 0) INITERROR;
    if (PyModule_AddIntMacro(m, PATCH) != 0) INITERROR;
    if (PyModule_AddIntConstant(m, "LIBXML_VERSION", atoi(xmlParserVersion)) != 0) INITERROR;
#if PY_MAJOR_VERSION >= 3
    return m;
#endif
}
