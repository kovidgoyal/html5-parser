/*
 * as-python-tree.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */
#include "as-python-tree.h"

// Stack {{{

#define Item1 GumboNode*
#define Item2 PyObject*
#define StackItemClass StackItem
#define StackClass Stack
#include "stack.h"

// }}}

static PyObject *KNOWN_TAG_NAMES, *KNOWN_ATTR_NAMES;

const char* ATTR_NAMES[] = {
#include "attr_strings.h"
  "",                   // ATTR_LAST
};

static const uint8_t ATTR_SIZES[] = {
#include "attr_sizes.h"
  0, // ATTR_LAST
};


#include "attr_perf.h"
#define ATTR_MAP_SIZE (sizeof(HTML_ATTR_MAP) / sizeof(HTML_ATTR_MAP[0]))


static inline HTMLAttr
attr_num(const char *attr, unsigned int length) {
    if (LIKELY(length)) {
        unsigned int key = attr_hash(attr, length);
        if (key < ATTR_MAP_SIZE) {
            HTMLAttr ans = HTML_ATTR_MAP[key];
            if (LIKELY(length == ATTR_SIZES[(int) ans] && !strncmp(attr, ATTR_NAMES[(int) ans], length))) return ans;
        }
    }
    return HTML_ATTR_LAST;
}


bool
set_known_tag_names(PyObject *val, PyObject *attr_val) {
    PyObject *tag_name;
    KNOWN_TAG_NAMES = val;
    for (int i = 0; i < GUMBO_TAG_UNKNOWN; i++) {
        tag_name = PyUnicode_FromString(gumbo_normalized_tagname(i));
        if (tag_name == NULL) return false;
        PyTuple_SET_ITEM(KNOWN_TAG_NAMES, i, tag_name);
    }
    KNOWN_ATTR_NAMES = attr_val;
    for (int i = 0; i < HTML_ATTR_LAST; i++) {
        tag_name = PyUnicode_FromString(ATTR_NAMES[i]);
        if (tag_name == NULL) return false;
        PyTuple_SET_ITEM(KNOWN_ATTR_NAMES, i, tag_name);
    }
    return true;
}


static inline bool
push_children(PyObject *parent, GumboElement *elem, Stack *stack) {
    for (int i = elem->children.length - 1; i >= 0; i--) {
        if (!Stack_push(stack, elem->children.data[i], parent)) return false;
    }
    return true;
}


static inline PyObject*
create_attr_name(const char *aname) {
    size_t alen = strlen(aname);
    HTMLAttr anum = attr_num(aname, alen);
    if (anum >= HTML_ATTR_LAST) return PyUnicode_FromStringAndSize(aname, alen);
    PyObject *ans = PyTuple_GET_ITEM(KNOWN_ATTR_NAMES, (int)anum);
    Py_INCREF(ans);
    return ans;
}

static inline PyObject*
create_attributes(GumboElement *elem) {
    GumboAttribute* attr;
    const char *aname;
    char buf[MAX_TAG_NAME_SZ];
    PyObject *attr_name = NULL, *attr_val = NULL, *ans;
    ans = PyDict_New();
    if (ans == NULL) return NULL;

    for (unsigned int i = 0; i < elem->attributes.length; ++i) {
#define ABORT { Py_CLEAR(ans); Py_CLEAR(attr_name); Py_CLEAR(attr_val); break; }
        attr = elem->attributes.data[i];
        aname = attr->name;
        switch (attr->attr_namespace) {
            case GUMBO_ATTR_NAMESPACE_XLINK:
                snprintf(buf, MAX_TAG_NAME_SZ - 1, "xlink:%s", aname);
                aname = buf;
                break;
            case GUMBO_ATTR_NAMESPACE_XML:
                snprintf(buf, MAX_TAG_NAME_SZ - 1, "xml:%s", aname);
                aname = buf;
                break;
            case GUMBO_ATTR_NAMESPACE_XMLNS:
                snprintf(buf, MAX_TAG_NAME_SZ - 1, "xmlns:%s", aname);
                aname = buf;
                break;
            default:
                break;
        }
        attr_name = create_attr_name(aname);
        attr_val = PyUnicode_FromString(attr->value);
        if (UNLIKELY(attr_name == NULL || attr_val == NULL)) ABORT;
        if (UNLIKELY(PyDict_SetItem(ans, attr_name, attr_val) != 0)) ABORT;
        Py_DECREF(attr_name); Py_DECREF(attr_val);
#undef ABORT
    }
    return ans;
}

static inline PyObject*
create_element(GumboElement *elem, PyObject *new_tag) {
    PyObject *tag_name = NULL, *tag_obj = NULL, *attributes = NULL;
    const char *tag;

    if (UNLIKELY(elem->tag >= GUMBO_TAG_UNKNOWN)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag_name = PyUnicode_FromStringAndSize(elem->original_tag.data, elem->original_tag.length);
    } else if (UNLIKELY(elem->tag_namespace == GUMBO_NAMESPACE_SVG)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag = gumbo_normalize_svg_tagname(&(elem->original_tag));
        if (tag) {
            tag_name = PyUnicode_FromStringAndSize(tag, elem->original_tag.length);
        } else {
            tag_name = PyTuple_GET_ITEM(KNOWN_TAG_NAMES, elem->tag);
            Py_INCREF(tag_name);
        }
    } else {
        tag_name = PyTuple_GET_ITEM(KNOWN_TAG_NAMES, elem->tag);
        Py_INCREF(tag_name);
    }
    if (UNLIKELY(tag_name == NULL)) return NULL;
    attributes = create_attributes(elem);
    if (UNLIKELY(attributes == NULL)) { Py_CLEAR(tag_name); return NULL; }
    tag_obj = PyObject_CallFunctionObjArgs(new_tag, tag_name, attributes, NULL);
    Py_DECREF(tag_name); Py_DECREF(attributes);
    if (UNLIKELY(tag_obj == NULL)) return NULL;
    return tag_obj;
}

static inline PyObject* 
convert_node(GumboNode* node, GumboElement **elem, PyObject *new_tag, PyObject *new_comment, PyObject *new_string) {
    PyObject *ans = NULL, *temp;
    *elem = NULL;

#define STRING_LIKE(converter) \
    temp = PyUnicode_FromString(node->v.text.text); \
    if (UNLIKELY(temp == NULL)) break; \
    ans = PyObject_CallFunctionObjArgs(converter, temp, NULL); \
    Py_DECREF(temp); 

    switch (node->type) {
        case GUMBO_NODE_ELEMENT:
        case GUMBO_NODE_TEMPLATE:
            *elem = &node->v.element;
            ans = create_element(*elem, new_tag);
            break;
        case GUMBO_NODE_TEXT:
        case GUMBO_NODE_WHITESPACE:
        case GUMBO_NODE_CDATA:
            STRING_LIKE(new_string);
            break;
        case GUMBO_NODE_COMMENT:
            STRING_LIKE(new_comment);
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "unknown gumbo node type");
            break;
    }
#undef STRING_LIKE
    return ans;
}


PyObject*
as_python_tree(GumboOutput *gumbo_output, Options *opts, PyObject *new_tag, PyObject *new_comment, PyObject *new_string, PyObject *append) {
#define ABORT { ok = false; goto end; }
    bool ok = true;
    GumboNode *gumbo;
    GumboElement *elem;
    PyObject *parent, *child, *ans = NULL, *ret;
    Stack *stack = Stack_alloc(opts->stack_size);
    if (stack == NULL) return PyErr_NoMemory();

    Stack_push(stack, gumbo_output->root, NULL);
    while(stack->length > 0) {
        Stack_pop(stack, &gumbo, &parent);
        child = convert_node(gumbo, &elem, new_tag, new_comment, new_string);
        if (UNLIKELY(!child)) ABORT;
        if (LIKELY(parent)) {
            ret = PyObject_CallFunctionObjArgs(append, parent, child, NULL);
            Py_DECREF(child);
            if (UNLIKELY(ret == NULL)) ABORT;
            Py_DECREF(ret);
        } else ans = child;
        if (elem != NULL) {
            if (UNLIKELY(!push_children(child, elem, stack))) { PyErr_NoMemory(); ABORT; }
        }
    }

end:
    Stack_free(stack);
    if (!ok) { Py_CLEAR(ans); }
    return ans;
#undef ABORT
}
