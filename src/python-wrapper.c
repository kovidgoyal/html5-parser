/*
 * python-wrapper.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */


#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "../gumbo/gumbo.h"
#include "as-libxml.h"
#include "as-python-tree.h"

#define MAJOR 0
#define MINOR 4
#define PATCH 6

static char *NAME =  "libxml2:xmlDoc";
static char *DESTRUCTOR = "destructor:xmlFreeDoc";

static inline libxml_doc*
convert_tree(GumboOutput *output, Options *opts) {
    char *errmsg = NULL;
    libxml_doc *doc = NULL;

    Py_BEGIN_ALLOW_THREADS;
    doc = convert_gumbo_tree_to_libxml_tree(output, opts, &errmsg);
    Py_END_ALLOW_THREADS;
    if (doc == NULL) {
        if (errmsg) PyErr_SetString(PyExc_Exception, errmsg);
        else PyErr_NoMemory();
    }
    return doc;
}

static inline libxml_doc*
parse_with_options(const char* buffer, size_t buffer_length, Options *opts) {
    GumboOutput *output = NULL;
    libxml_doc* doc = NULL;
    Py_BEGIN_ALLOW_THREADS;
    output = gumbo_parse_with_options(&(opts->gumbo_opts), buffer, buffer_length);
    Py_END_ALLOW_THREADS;
    if (output == NULL) PyErr_NoMemory();
    else {
        doc = convert_tree(output, opts);
        gumbo_destroy_output(output);
    }
    return doc;
}

static void
free_encapsulated_doc(PyObject *capsule) {
    libxml_doc *doc = (libxml_doc*)PyCapsule_GetPointer(capsule, NAME);
    if (doc != NULL) {
        char *ctx = PyCapsule_GetContext(capsule);
        if (ctx == DESTRUCTOR) free_libxml_doc(doc);
    }
}

static inline PyObject*
encapsulate(libxml_doc* doc) {
    PyObject *ans = NULL;
    ans = PyCapsule_New(doc, NAME, free_encapsulated_doc);
    if (ans == NULL) { free_libxml_doc(doc); return NULL; }
    if (PyCapsule_SetContext(ans, DESTRUCTOR) != 0) { Py_DECREF(ans); return NULL; }
    return ans;
}

static PyObject *
parse(PyObject UNUSED *self, PyObject *args, PyObject *kwds) {
    libxml_doc *doc = NULL;
    const char *buffer = NULL;
    Py_ssize_t sz = 0;
    Options opts = {0};
    opts.stack_size = 16 * 1024;
    PyObject *kd = Py_True, *mx = Py_False, *ne = Py_False, *sn = Py_True;
    opts.gumbo_opts = kGumboDefaultOptions;
    opts.gumbo_opts.max_errors = 0;  // We discard errors since we are not reporting them anyway

    static char *kwlist[] = {"data", "namespace_elements", "keep_doctype", "maybe_xhtml", "line_number_attr", "sanitize_names", "stack_size", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s#|OOOzOI", kwlist, &buffer, &sz, &ne, &kd, &mx, &(opts.line_number_attr), &sn, &(opts.stack_size))) return NULL;
    opts.namespace_elements = PyObject_IsTrue(ne);
    opts.keep_doctype = PyObject_IsTrue(kd);
    opts.sanitize_names = PyObject_IsTrue(sn);
    opts.gumbo_opts.use_xhtml_rules = PyObject_IsTrue(mx);

    doc = parse_with_options(buffer, (size_t)sz, &opts);
    if (!doc) return NULL;
    return encapsulate(doc);
}


static PyObject *
parse_and_build(PyObject UNUSED *self, PyObject *args) {
    const char *buffer = NULL;
    Py_ssize_t sz = 0;
    GumboOutput *output = NULL;
    PyObject *new_tag, *new_comment, *ans, *new_doctype, *append, *new_string, *ret;
    Options opts = {0};
    opts.stack_size = 16 * 1024;
    opts.gumbo_opts = kGumboDefaultOptions;
    opts.gumbo_opts.max_errors = 0;  // We discard errors since we are not reporting them anyway

    if (!PyArg_ParseTuple(args, "s#OOOOO|I", &buffer, &sz, &new_tag, &new_comment, &new_string, &append, &new_doctype, &(opts.stack_size))) return NULL;
    Py_BEGIN_ALLOW_THREADS;
    output = gumbo_parse_with_options(&(opts.gumbo_opts), buffer, (size_t)sz);
    Py_END_ALLOW_THREADS;
    if (output == NULL) PyErr_NoMemory();
    GumboDocument* document = &(output->document->v.document);

    if (new_doctype != Py_None && document->has_doctype) {
        ret = PyObject_CallFunction(new_doctype, "sss", document->name, document->public_identifier, document->system_identifier);
        if (ret == NULL) { gumbo_destroy_output(output); return NULL; }
        Py_CLEAR(ret);
    }
    ans = as_python_tree(output, &opts, new_tag, new_comment, new_string, append);
    gumbo_destroy_output(output);
    return ans;
}


static PyObject *
clone_doc(PyObject UNUSED *self, PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) { PyErr_SetString(PyExc_TypeError, "Must specify a capsule as the argument"); return NULL; }
    libxml_doc *sdoc = PyCapsule_GetPointer(capsule, PyCapsule_GetName(capsule)), *doc;
    if (sdoc == NULL) return NULL;
    doc = copy_libxml_doc(sdoc);
    if (doc == NULL) return PyErr_NoMemory();
    return encapsulate(doc);
}

static PyMethodDef
methods[] = {
    {"parse", (PyCFunction)(void(*)(void))(PyCFunctionWithKeywords)(parse), METH_VARARGS | METH_KEYWORDS,
        "parse()\n\nParse specified bytestring which must be in the UTF-8 encoding."
    },

    {"parse_and_build", (PyCFunction)parse_and_build, METH_VARARGS,
        "parse_and_build()\n\nParse specified bytestring which must be in the UTF-8 encoding and build a tree using the specified functions."
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

EXPORTED PyMODINIT_FUNC
PyInit_html_parser(void) {

#else
#define INITERROR return
EXPORTED PyMODINIT_FUNC
inithtml_parser(void) {
#endif
    PyObject *m, *known_tag_names, *known_attr_names;
#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule3(MODULE_NAME, methods, MODULE_DOC);
#endif
    if (m == NULL) INITERROR;
    if (PyModule_AddIntMacro(m, MAJOR) != 0) INITERROR;
    if (PyModule_AddIntMacro(m, MINOR) != 0) INITERROR;
    if (PyModule_AddIntMacro(m, PATCH) != 0) INITERROR;
    if (PyModule_AddIntConstant(m, "LIBXML_VERSION", get_libxml_version()) != 0) INITERROR;
    known_tag_names = PyTuple_New(GUMBO_TAG_UNKNOWN);
    if (known_tag_names == NULL) INITERROR;
    if (PyModule_AddObject(m, "KNOWN_TAG_NAMES", known_tag_names) != 0) { Py_CLEAR(known_tag_names); INITERROR; }
    known_attr_names = PyTuple_New(HTML_ATTR_LAST);
    if (known_attr_names == NULL) INITERROR;
    if (PyModule_AddObject(m, "KNOWN_ATTR_NAMES", known_attr_names) != 0) { Py_CLEAR(known_attr_names); INITERROR; }
    if (!set_known_tag_names(known_tag_names, known_attr_names)) { Py_CLEAR(known_tag_names); Py_CLEAR(known_attr_names); INITERROR; }
#if PY_MAJOR_VERSION >= 3
    return m;
#endif
}
