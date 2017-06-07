/*
 * as-libxml.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */


#include <assert.h>
#include <string.h>

#include "as-libxml.h"
#include <libxml/tree.h>
#include <libxml/dict.h>

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
                if (UNLIKELY(strncmp(aname, "xml:lang", 8) == 0)) {
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

static inline xmlDocPtr
alloc_doc(void) {
    xmlDocPtr doc = xmlNewDoc(BAD_CAST "1.0");
    if (doc) {
        if (!doc->dict) {
            doc->dict = xmlDictCreate();
            if (doc->dict == NULL) {
                xmlFreeDoc(doc);
                doc = NULL;
            }
        }
    }
    return doc;
}

libxml_doc*
convert_gumbo_tree_to_libxml_tree(GumboOutput *output, Options *opts, char **errmsg) {
#define ABORT { ok = false; goto end; }
    xmlDocPtr doc = NULL;
    xmlNodePtr parent = NULL, child = NULL;
    GumboNode *gumbo = NULL, *root = output->root;
    ParseData parse_data = {0};
    GumboElement *elem;
    bool ok = true;
    *errmsg = NULL;
    Stack *stack = alloc_stack(opts->stack_size);
    if (stack == NULL) return NULL;
    stack_push(stack, root, NULL);
    doc = alloc_doc();
    if (doc == NULL) ABORT;

    if (opts->keep_doctype) {
        GumboDocument* doctype = & output->document->v.document;
        if(!xmlCreateIntSubset(doc, BAD_CAST doctype->name, BAD_CAST doctype->public_identifier, BAD_CAST doctype->system_identifier)) ABORT;
    }

    parse_data.maybe_xhtml = opts->gumbo_opts.use_xhtml_rules;
    doc->_private = (void*)&parse_data;
    while(stack->length > 0) {
        stack_pop(stack, &gumbo, &parent);
        child = convert_node(doc, parent, gumbo, &elem, opts);
        if (UNLIKELY(!child)) ABORT;
        if (LIKELY(parent)) {
            if (UNLIKELY(!xmlAddChild(parent, child))) ABORT;
        } else parse_data.root = child; 
        if (elem != NULL) {
            if (!push_children(child, elem, stack)) ABORT;
        }

    }
#undef ABORT
end:
    if (doc) doc->_private = NULL;
    free_stack(stack);
    *errmsg = (char*)parse_data.errmsg;
    if (ok) xmlDocSetRootElement(doc, parse_data.root);
    else { if (parse_data.root) xmlFreeNode(parse_data.root); if (doc) xmlFreeDoc(doc); doc = NULL; }
    return doc;
}

libxml_doc* 
copy_libxml_doc(libxml_doc* doc) { return xmlCopyDoc(doc, 1); }

libxml_doc 
free_libxml_doc(libxml_doc* doc) { xmlFreeDoc(doc); }

int
get_libxml_version(void) {
    return atoi(xmlParserVersion);
}
