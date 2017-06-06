/*
 * gumbo-libxml.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

// Based on https://github.com/nostrademons/gumbo-libxml/blob/master/gumbo_libxml.c


#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <libxml/tree.h>
#include <libxml/dict.h>
#include <libxml/xmlversion.h>

#include <assert.h>
#include <string.h>

#include "../gumbo/gumbo.h"

#define MAJOR 0
#define MINOR 2
#define PATCH 1
#ifdef _MSC_VER
#define UNUSED 
#else
#define UNUSED __attribute__ ((unused))
#endif
#ifdef __builtin_expect
#define LIKELY(x)    __builtin_expect (!!(x), 1)
#define UNLIKELY(x)  __builtin_expect (!!(x), 0)
#else
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#endif

// Namespace constants, indexed by GumboNamespaceEnum.
static const char* kLegalXmlns[] = {
    "http://www.w3.org/1999/xhtml",
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/1998/Math/MathML"
};

typedef struct {
    xmlNsPtr xlink, xml;
    xmlNodePtr root;
    bool maybe_xhtml;
    const char* errmsg;
} ParseData;

// Stack {{{

typedef struct {
    GumboNode *gumbo;
    xmlNodePtr xml;
} StackItem;

typedef struct {
    size_t length;
    size_t capacity;
    StackItem *items;
} Stack;

static inline Stack*
alloc_stack(size_t sz) {
    Stack *ans = (Stack*)calloc(sizeof(Stack), 1);
    if (ans) {
        ans->items = (StackItem*)malloc(sizeof(StackItem) * sz);
        if (ans->items) ans->capacity = sz;
        else { free(ans); ans = NULL; }
    }
    return ans;
}

static inline void
free_stack(Stack *s) { if (s) { free(s->items); free(s); } }

static inline void
stack_pop(Stack *s, GumboNode **g, xmlNodePtr *x) { StackItem *si = &(s->items[--(s->length)]); *g = si->gumbo; *x = si->xml; }

static inline void*
safe_realloc(void *p, size_t sz) {
    void *orig = p;
    void *ans = realloc(p, sz);
    if (ans == NULL) free(orig);
    return ans;
}

static inline bool
stack_push(Stack *s, GumboNode *g, xmlNodePtr x) {
    if (s->length >= s->capacity) {
        s->capacity *= 2;
        s->items = (StackItem*)safe_realloc(s->items, s->capacity * sizeof(StackItem));
        if (!s->items) return false;
    }
    StackItem *si = &(s->items[(s->length)++]);
    si->gumbo = g; si->xml = x;
    return true;
}
// }}}

typedef struct {
    unsigned int stack_size;
    bool keep_doctype, namespace_elements;
    GumboOptions gumbo_opts;
} Options;

static inline bool
push_children(xmlNodePtr parent, GumboElement *elem, Stack *stack) {
    for (int i = elem->children.length - 1; i >= 0; i--) {
        if (!stack_push(stack, elem->children.data[i], parent)) return false;
    }
    return true;
}

static inline xmlNsPtr
ensure_xml_ns(xmlDocPtr doc, ParseData *pd, xmlNodePtr node) {
    // By default libxml2 docs do not have the xml: namespace defined.
    xmlNodePtr root = pd->root ? pd->root : node;
    if (UNLIKELY(!pd->xml)) {
        pd->xml = xmlSearchNs(doc, root, BAD_CAST "xml");
    }
    return pd->xml;
}

static inline bool
create_attributes(xmlDocPtr doc, xmlNodePtr node, GumboElement *elem) {
    GumboAttribute* attr;
    const xmlChar *attr_name;
    const char *aname;
    char buf[50] = {0};
    ParseData *pd = (ParseData*)doc->_private;
    xmlNsPtr ns;
    xmlNodePtr root;

    for (unsigned int i = 0; i < elem->attributes.length; ++i) {
        attr = elem->attributes.data[i];
        aname = attr->name;
        ns = NULL;
        switch (attr->attr_namespace) {
            case GUMBO_ATTR_NAMESPACE_XLINK:
                root = pd->root ? pd->root : node;
                if (UNLIKELY(!pd->xlink)) {
                    pd->xlink = xmlNewNs(root, BAD_CAST "http://www.w3.org/1999/xlink", BAD_CAST "xlink");
                    if(UNLIKELY(!pd->xlink)) return false;
                }
                ns = pd->xlink;
                break;
            case GUMBO_ATTR_NAMESPACE_XML:
                ns = ensure_xml_ns(doc, pd, node);
                if (UNLIKELY(!ns)) return false;
                break;
            case GUMBO_ATTR_NAMESPACE_XMLNS:
                if (strncmp(aname, "xlink", 5) == 0) {
                    root = pd->root ? pd->root : node;
                    if (UNLIKELY(!pd->xlink)) {
                        pd->xlink = xmlNewNs(root, BAD_CAST "http://www.w3.org/1999/xlink", BAD_CAST "xlink");
                        if(UNLIKELY(!pd->xlink)) return false;
                    }
                    // We ignore the value of this attribute since we dont want
                    // the xlink namespace to be redefined
                    continue;
                } else if (strncmp(aname, "xmlns", 5) == 0) {
                    // discard since we dont support changing the default
                    // namespace, namespace are decided by tag names alone. 
                    continue; 
                }
                break;
            default:
                if (UNLIKELY(pd->maybe_xhtml && strncmp(aname, "xml:lang", 8) == 0)) {
                    aname = "lang";
                    ns = ensure_xml_ns(doc, pd, node);
                    if (UNLIKELY(!ns)) return false;
                } else if (UNLIKELY(strncmp("xmlns", aname, 5) == 0)) {
                    size_t len = strlen(aname);
                    if (len == 5) continue;  // ignore xmlns 
                    if (aname[5] == ':') {
                        if (len == 6) continue; //ignore xmlns:
                        snprintf(buf, sizeof(buf) - 1, "xmlns-%s", aname + 6);
                        aname = buf;
                    }
                }
                break;
        }
        attr_name = xmlDictLookup(doc->dict, BAD_CAST aname, -1);
        if (UNLIKELY(!attr_name)) return false;
        if (UNLIKELY(!xmlNewNsPropEatName(node, ns, (xmlChar*)attr_name, BAD_CAST attr->value))) return false;
    }
    return true;
}

static inline uint8_t
copy_tag_name(GumboStringPiece *src, char* dest, size_t destsz) {
    uint8_t i = 0;
    for (; i < destsz && i < src->length; i++) {
        char ch = src->data[i];
        if (ch == ':') ch = '-';
        dest[i] = ch;
    }
    return i;
}


static inline xmlNodePtr
create_element(xmlDocPtr doc, xmlNodePtr xml_parent, GumboNode *parent, GumboElement *elem, bool namespace_elements) {
#define ABORT { ok = false; goto end; }
    xmlNodePtr result = NULL;
    bool ok = true;
    const xmlChar *tag_name = NULL;
    const char *tag;
    uint8_t tag_sz;
    char buf[50] = {0};
    xmlNsPtr namespace = NULL;


    if (elem->tag == GUMBO_TAG_UNKNOWN) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag_sz = copy_tag_name(&(elem->original_tag), buf, sizeof(buf));
        tag = buf;
    } else if (elem->tag_namespace == GUMBO_NAMESPACE_SVG) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag = gumbo_normalize_svg_tagname(&(elem->original_tag), &tag_sz);
        if (tag == NULL) tag = gumbo_normalized_tagname_and_size(elem->tag, &tag_sz);
    } else tag = gumbo_normalized_tagname_and_size(elem->tag, &tag_sz);

    tag_name = xmlDictLookup(doc->dict, BAD_CAST tag, tag_sz);
    if (UNLIKELY(!tag_name)) ABORT;

    // Must use xmlNewDocNodeEatName as we are using a dict string and without this
    // if an error occurs and we have to call xmlFreeNode before adding this node to the doc
    // we get a segfault.
    result = xmlNewDocNodeEatName(doc, NULL, (xmlChar*)tag_name, NULL);
    if (UNLIKELY(!result)) ABORT;

    if (namespace_elements) {
        if (UNLIKELY(parent->type == GUMBO_NODE_DOCUMENT || elem->tag_namespace != parent->v.element.tag_namespace)) {
            // Default namespace has changed
            namespace = xmlNewNs(
                    result, BAD_CAST kLegalXmlns[elem->tag_namespace], NULL);
            if (UNLIKELY(!namespace)) ABORT;
            xmlSetNs(result, namespace);
        } else {
            xmlSetNs(result, xml_parent->ns);
        }
    }

    ok = create_attributes(doc, result, elem);
#undef ABORT
end:
    if (UNLIKELY(!ok)) { 
        if(result) xmlFreeNode(result); 
        result = NULL; 
    }
    return result;
}


static inline xmlNodePtr 
convert_node(xmlDocPtr doc, xmlNodePtr xml_parent, GumboNode* node, GumboElement **elem, Options *opts) {
    xmlNodePtr ans = NULL;
    ParseData *pd = (ParseData*)doc->_private;
    *elem = NULL;

    switch (node->type) {
        case GUMBO_NODE_ELEMENT:
        case GUMBO_NODE_TEMPLATE:
            *elem = &node->v.element;
            ans = create_element(doc, xml_parent, node->parent, *elem, opts->namespace_elements);
            break;
        case GUMBO_NODE_TEXT:
        case GUMBO_NODE_WHITESPACE:
            ans = xmlNewText(BAD_CAST node->v.text.text);
            break;
        case GUMBO_NODE_COMMENT:
            ans = xmlNewComment(BAD_CAST node->v.text.text);
            break;
        case GUMBO_NODE_CDATA:
            {
                // TODO: probably would be faster to use some calculation on
                // original_text.length rather than strlen, but I haven't verified that
                // that's correct in all cases.
                const char* node_text = node->v.text.text;
                ans = xmlNewCDataBlock(doc, BAD_CAST node_text, (int)strlen(node_text));
            }
            break;
        default:
            pd->errmsg =  "unknown gumbo node type";
            break;
    }
    return ans;
}

static xmlNodePtr
convert_tree(xmlDocPtr doc, GumboNode *root, Options *opts) {
    xmlNodePtr parent = NULL, child = NULL;
    GumboNode *gumbo = NULL;
    ParseData parse_data = {0};
    bool ok = true;
    GumboElement *elem;
    Stack *stack = alloc_stack(opts->stack_size);

    if (stack == NULL) { PyErr_NoMemory(); return NULL; }
    stack_push(stack, root, NULL);

    Py_BEGIN_ALLOW_THREADS;
    parse_data.maybe_xhtml = opts->gumbo_opts.use_xhtml_rules;
    doc->_private = (void*)&parse_data;
    while(stack->length > 0) {
        stack_pop(stack, &gumbo, &parent);
        child = convert_node(doc, parent, gumbo, &elem, opts);
        if (UNLIKELY(!child)) { ok = false;  goto end; };
        if (LIKELY(parent)) {
            if (UNLIKELY(!xmlAddChild(parent, child))) { ok = false; goto end; }
        } else parse_data.root = child; 
        if (elem != NULL) {
            if (!push_children(child, elem, stack)) { ok = false; goto end; };
        }

    }
end:
    doc->_private = NULL;
    Py_END_ALLOW_THREADS;
    if (!ok) {
        if (parse_data.root) { xmlFreeNode(parse_data.root); parse_data.root = NULL; }
        if (!PyErr_Occurred()) {
            if (parse_data.errmsg) PyErr_SetString(PyExc_Exception, parse_data.errmsg);
            else PyErr_NoMemory();
        }
    }
    free_stack(stack);
    return parse_data.root;
}

static bool 
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
    root = convert_tree(doc, output->root, opts);
    if (root) xmlDocSetRootElement(doc, root);
    gumbo_destroy_output(output);
    return root ? true : false;
}

// Python wrapper {{{

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

    doc = xmlNewDoc(BAD_CAST "1.0");
    if (doc == NULL) return PyErr_NoMemory();
    if (doc->dict == NULL) {
        doc->dict = xmlDictCreate();
        if (doc->dict == NULL) {
            xmlFreeDoc(doc);
            return PyErr_NoMemory();
        }
    }

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
// }}}
