/*
 * gumbo-libxml.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

// Based on https://github.com/nostrademons/gumbo-libxml/blob/master/gumbo_libxml.c

#include "../gumbo/gumbo.h"

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <libxml/tree.h>

#include <assert.h>
#include <string.h>

#define UNUSED __attribute__ ((unused))

// Namespace constants, indexed by GumboNamespaceEnum.
static const char* kLegalXmlns[] = {
    "http://www.w3.org/1999/xhtml",
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/1998/Math/MathML"
};

static xmlNodePtr 
convert_node(xmlDocPtr doc, GumboNode* node) {
    xmlNodePtr result = NULL, child = NULL;
    switch (node->type) {
        case GUMBO_NODE_DOCUMENT:
            assert(false &&
                    "convert_node cannot be used on the document node.  "
                    "Doctype information is automatically added to the xmlDocPtr.");
            break;
        case GUMBO_NODE_ELEMENT:
        case GUMBO_NODE_TEMPLATE:
            {
                GumboElement* elem = &node->v.element;
                // Tag name & namespace.
                result = xmlNewNode(NULL, BAD_CAST gumbo_normalized_tagname(elem->tag));
                if (result) {
                    xmlNsPtr namespace = NULL;
                    if (node->parent->type != GUMBO_NODE_DOCUMENT &&
                            elem->tag_namespace != node->parent->v.element.tag_namespace) {
                        namespace = xmlNewNs(
                                result, BAD_CAST kLegalXmlns[elem->tag_namespace], NULL);
                        xmlSetNs(result, namespace);
                    }
                    // Attributes.
                    for (unsigned int i = 0; i < elem->attributes.length; ++i) {
                        GumboAttribute* attr = elem->attributes.data[i];
                        xmlNewProp(result, BAD_CAST attr->name, BAD_CAST attr->value);
                    }

                    // Children.
                    for (unsigned int i = 0; i < elem->children.length; ++i) {
                        child = convert_node(doc, elem->children.data[i]);
                        if (child) xmlAddChild(result, child);
                        else break;
                    }
                } 
            }
            break;
        case GUMBO_NODE_TEXT:
        case GUMBO_NODE_WHITESPACE:
            result = xmlNewText(BAD_CAST node->v.text.text);
            break;
        case GUMBO_NODE_COMMENT:
            result = xmlNewComment(BAD_CAST node->v.text.text);
            break;
        case GUMBO_NODE_CDATA:
            {
                // TODO: probably would be faster to use some calculation on
                // original_text.length rather than strlen, but I haven't verified that
                // that's correct in all cases.
                const char* node_text = node->v.text.text;
                result = xmlNewCDataBlock(doc, BAD_CAST node_text, strlen(node_text));
            }
            break;
        default:
            assert(false && "unknown node type");
    }
    if (!result && !PyErr_Occurred()) PyErr_NoMemory();
    return result;
}

static bool 
parse_with_options(xmlDocPtr doc, GumboOptions* options, const char* buffer, size_t buffer_length, bool keep_doctype) {
    GumboOutput *output = NULL;
    xmlNodePtr root = NULL;
    output = gumbo_parse_with_options(options, buffer, buffer_length);
    if (output == NULL) { PyErr_NoMemory(); return false; }
    if (keep_doctype) {
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
    root = convert_node(doc, output->root);
    if (root) xmlDocSetRootElement(doc, root);
    gumbo_destroy_output(output);
    return root ? true : false;
}


static char *NAME =  "libxml2:xmlDoc";
static char *DESTRUCTOR = "destructor:xmlFreeDoc";

static void 
free_encapsulated_doc(PyObject *capsule) {
    xmlDocPtr doc = PyCapsule_GetPointer(capsule, NAME);
    if (doc != NULL) {
        char *ctx = PyCapsule_GetContext(capsule);
        if (ctx == DESTRUCTOR) xmlFreeDoc(doc);
    }
}

static PyObject *
parse(PyObject UNUSED *self, PyObject *args) {
    GumboOptions options = kGumboDefaultOptions;
    xmlDocPtr doc = NULL;
    char *buffer = NULL;
    Py_ssize_t sz = 0;
    PyObject *ans = NULL;

    if (!PyArg_ParseTuple(args, "s#", &buffer, &sz)) return NULL;

    doc = xmlNewDoc(BAD_CAST "1.0");
    if (doc == NULL) return PyErr_NoMemory();

    if (!parse_with_options(doc, &options, buffer, (size_t)sz, false)) { xmlFreeDoc(doc); return NULL; }
    ans = PyCapsule_New(doc, NAME, free_encapsulated_doc);
    if (ans == NULL) { xmlFreeDoc(doc); return NULL; }
    if (PyCapsule_SetContext(ans, DESTRUCTOR) != 0) { Py_DECREF(ans); return NULL; }
    return ans;
}


static PyMethodDef 
methods[] = {
    {"parse", parse, METH_VARARGS,
        "parse()\n\nParse specified bytestring which must be in the UTF-8 encoding."
    },

    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
inithtml_parser(void) {
    PyObject *m;
    m = Py_InitModule3("html_parser", methods,
    "HTML parser in C for speed."
    );
    if (m == NULL) return;
}
