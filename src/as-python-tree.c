/*
 * as-python-tree.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */
#define NEEDS_SANITIZE_NAME 1
#include "as-python-tree.h"
static PyObject *KNOWN_TAG_NAMES;

#define CALL_METHOD1(obj, name, arg) \
    meth = PyObject_GetAttrString(obj, name); \
    if (meth != NULL) { ret = PyObject_CallFunctionObjArgs(meth, arg, NULL); Py_DECREF(meth); } \
    else ret = NULL;

bool
set_known_tag_names(PyObject *val) {
    PyObject *tag_name;
    KNOWN_TAG_NAMES = val;
    for (int i = 0; i < GUMBO_TAG_UNKNOWN; i++) {
        tag_name = PyUnicode_FromString(gumbo_normalized_tagname(i));
        if (tag_name == NULL) return false;
        PyTuple_SET_ITEM(KNOWN_TAG_NAMES, i, tag_name);
    }
    return true;
}

// Stack {{{

#define Item1 GumboNode*
#define Item2 PyObject*
#define StackItemClass StackItem
#define StackClass Stack
#include "stack.h"

// }}}

static inline bool
push_children(PyObject *parent, GumboElement *elem, Stack *stack) {
    for (int i = elem->children.length - 1; i >= 0; i--) {
        if (!Stack_push(stack, elem->children.data[i], parent)) return false;
    }
    return true;
}

static inline PyObject*
create_element(GumboElement *elem, PyObject *new_tag) {
    PyObject *tag_name = NULL, *ret;
    char buf[MAX_TAG_NAME_SZ] = {0};
    uint8_t tag_sz;
    const char *tag;

    if (UNLIKELY(elem->tag >= GUMBO_TAG_UNKNOWN)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag_sz = MIN(sizeof(buf) - 1, elem->original_tag.length);
        memcpy(buf, elem->original_tag.data, tag_sz);
        tag = buf;
        tag_sz = sanitize_name((char*)tag);
        tag_name = PyUnicode_FromStringAndSize(tag, tag_sz);
    } else if (UNLIKELY(elem->tag_namespace == GUMBO_NAMESPACE_SVG)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag = gumbo_normalize_svg_tagname(&(elem->original_tag), &tag_sz);
        if (tag) {
            tag_name = PyUnicode_FromStringAndSize(tag, tag_sz);
        } else {
            tag_name = PyTuple_GET_ITEM(KNOWN_TAG_NAMES, elem->tag);
            Py_INCREF(tag_name);
        }
    } else {
        tag_name = PyTuple_GET_ITEM(KNOWN_TAG_NAMES, elem->tag);
        Py_INCREF(tag_name);
    }
    if (UNLIKELY(tag_name == NULL)) return NULL;
    ret = PyObject_CallFunctionObjArgs(new_tag, tag_name, NULL);
    if (UNLIKELY(ret == NULL)) { Py_CLEAR(tag_name); return NULL; }
    return ret;
}

static inline PyObject* 
convert_node(GumboNode* node, GumboElement **elem, PyObject *new_tag, PyObject *new_comment) {
    PyObject *ans = NULL, *temp;
    *elem = NULL;

    switch (node->type) {
        case GUMBO_NODE_ELEMENT:
        case GUMBO_NODE_TEMPLATE:
            *elem = &node->v.element;
            ans = create_element(*elem, new_tag);
            break;
        case GUMBO_NODE_TEXT:
        case GUMBO_NODE_WHITESPACE:
        case GUMBO_NODE_CDATA:
            ans = PyUnicode_FromString(node->v.text.text);
            break;
        case GUMBO_NODE_COMMENT:
            temp = PyUnicode_FromString(node->v.text.text);
            if (temp == NULL) break;
            ans = PyObject_CallFunctionObjArgs(new_comment, temp, NULL);
            Py_CLEAR(temp);
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "unknown gumbo node type");
            break;
    }
    return ans;
}


PyObject*
as_python_tree(GumboOutput *gumbo_output, Options *opts, PyObject *new_tag, PyObject *new_comment) {
#define ABORT { ok = false; goto end; }
    bool ok = true;
    GumboNode *gumbo;
    GumboElement *elem;
    PyObject *parent, *child, *ans = NULL, *ret, *meth;
    Stack *stack = Stack_alloc(opts->stack_size);
    if (stack == NULL) return PyErr_NoMemory();

    Stack_push(stack, gumbo_output->root, NULL);
    while(stack->length > 0) {
        Stack_pop(stack, &gumbo, &parent);
        child = convert_node(gumbo, &elem, new_tag, new_comment);
        if (UNLIKELY(!child)) ABORT;
        if (LIKELY(parent)) {
            CALL_METHOD1(parent, "append", child);
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
