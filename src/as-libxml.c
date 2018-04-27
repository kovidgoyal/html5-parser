/*
 * as-libxml.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */


#include <assert.h>
#include <string.h>

#define NEEDS_SANITIZE_NAME 1
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
    bool maybe_xhtml, sanitize_names;
    const char* errmsg;
    const xmlChar* standard_tags[GUMBO_TAG_LAST], *lang_attribute;
} ParseData;

// Stack {{{

#define Item1 GumboNode*
#define Item2 xmlNodePtr
#define StackItemClass StackItem
#define StackClass Stack
#include "stack.h"

// }}}

static inline bool
push_children(xmlNodePtr parent, GumboElement *elem, Stack *stack) {
    for (int i = elem->children.length - 1; i >= 0; i--) {
        if (!Stack_push(stack, elem->children.data[i], parent)) return false;
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

static inline xmlNsPtr
find_namespace_by_prefix(xmlDocPtr doc, xmlNodePtr node, xmlNodePtr xml_parent, const char* prefix) {
    xmlNsPtr ans = xmlSearchNs(doc, node, BAD_CAST prefix);
    if (ans) return ans;
    if (!xml_parent) return NULL;
    return xmlSearchNs(doc, xml_parent, BAD_CAST prefix);
}

static GumboStringPiece REPROCESS = {"", 0};

static inline bool
create_attributes(xmlDocPtr doc, xmlNodePtr node, GumboElement *elem, xmlNodePtr xml_parent, bool reprocess, bool *needs_reprocess) {
    GumboAttribute* attr;
    const xmlChar *attr_name;
    const char *aname;
    char buf[50] = {0};
    ParseData *pd = (ParseData*)doc->_private;
    xmlNsPtr ns;
    xmlNodePtr root;
    int added_lang = 0;

    for (unsigned int i = 0; i < elem->attributes.length; ++i) {
        attr = elem->attributes.data[i];
        if (reprocess && attr->original_name.data != REPROCESS.data) continue;
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
                if (UNLIKELY(pd->maybe_xhtml && strcmp(aname, "lang") == 0)) {
                    if (!added_lang) {
                        added_lang = 1;
                        if (UNLIKELY(!xmlNewNsPropEatName(node, NULL, (xmlChar*)pd->lang_attribute, BAD_CAST attr->value))) return false;
                    }
                    continue;
                }
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
                    if (!added_lang) {
                        added_lang = 1;
                        if (UNLIKELY(!xmlNewNsPropEatName(node, ns, (xmlChar*)pd->lang_attribute, BAD_CAST attr->value))) return false;
                    }
                    continue;
                } else if (UNLIKELY(strncmp("xmlns", aname, 5) == 0)) {
                    size_t len = strlen(aname);
                    if (len == 5) continue;  // ignore xmlns
                    if (aname[5] == ':') {
                        if (len == 6) continue; //ignore xmlns:
                        if (pd->maybe_xhtml) {
                            xmlNewNs(node, BAD_CAST attr->value, BAD_CAST aname + 6);
                            // We ignore failure to create the namespace as the most likely
                            // cause is the prefix already exists in this context and xmlNewNs
                            // does not allow replacing prefixes. We could in theory find the
                            // existing namespace, but I dont care enough
                            continue;
                        } else {
                            snprintf(buf, sizeof(buf) - 1, "xmlns_%s", aname + 6);
                            aname = buf;
                        }
                    }
                }
                break;
        }

        if (pd->maybe_xhtml) {
            char *colon = strchr(aname, ':');
            if (colon && strlen(colon + 1) > 0) {
                *colon = 0;
                ns = find_namespace_by_prefix(doc, node, xml_parent, aname);
                *colon = ':';
                if (!ns) {
                    if (!reprocess) {
                        attr->original_name.data = REPROCESS.data;
                        *needs_reprocess = true;
                        continue;
                    }
                    *colon = '_';
                } else aname = colon + 1;
            }
        }
        attr_name = xmlDictLookup(doc->dict, BAD_CAST aname, (pd->sanitize_names ? sanitize_name((char*)aname) : strlen(aname)));  // we deliberately discard const, for performance
        if (UNLIKELY(!attr_name)) return false;
        if (UNLIKELY(pd->maybe_xhtml && attr_name == pd->lang_attribute)) {
            if (added_lang == 2) continue;
            added_lang = 2;
            xmlSetNsProp(node, NULL, attr_name, BAD_CAST attr->value);
        } else {
            if (UNLIKELY(!xmlNewNsPropEatName(node, ns, (xmlChar*)attr_name, BAD_CAST attr->value))) return false;
        }
    }
    return true;
}

static inline char*
check_for_namespace_prefix(char **tag, uint8_t *sz) {
    char *colon = memchr(*tag, ':', *sz);
    if (!colon || (size_t)(colon + 1 - *tag) >= *sz) return NULL;
    *sz -= colon + 1 - *tag;
    *colon = 0;
    char *ans = *tag;
    *tag = colon + 1;
    return ans;
}


static inline const xmlChar*
lookup_standard_tag(xmlDocPtr doc, ParseData *pd, GumboTag tag) {
    if (UNLIKELY(!pd->standard_tags[tag])) {
        uint8_t tag_sz;
        const char *name = gumbo_normalized_tagname_and_size(tag, &tag_sz);
        pd->standard_tags[tag] = xmlDictLookup(doc->dict, BAD_CAST name, tag_sz);
    }
    return pd->standard_tags[tag];
}

static inline xmlNodePtr
create_element(xmlDocPtr doc, xmlNodePtr xml_parent, GumboNode *parent, GumboElement *elem, Options *opts) {
#define ABORT { ok = false; goto end; }
    xmlNodePtr result = NULL;
    bool ok = true;
    const xmlChar *tag_name = NULL;
    const char *tag;
    char buf[MAX_TAG_NAME_SZ] = {0};
    char *nsprefix = NULL;
    xmlNsPtr namespace = NULL;
    ParseData *pd = (ParseData*)doc->_private;


    if (UNLIKELY(elem->tag >= GUMBO_TAG_UNKNOWN)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        uint8_t tag_sz = MIN(sizeof(buf) - 1, elem->original_tag.length);
        memcpy(buf, elem->original_tag.data, tag_sz);
        tag = buf;
        if (pd->maybe_xhtml) {
            char *temp = buf;
            nsprefix = check_for_namespace_prefix(&temp, &tag_sz);
            tag = temp;
        }
        tag_sz = pd->sanitize_names ? sanitize_name((char*)tag) : strlen(tag);
        tag_name = xmlDictLookup(doc->dict, BAD_CAST tag, tag_sz);
    } else if (UNLIKELY(elem->tag_namespace == GUMBO_NAMESPACE_SVG)) {
        gumbo_tag_from_original_text(&(elem->original_tag));
        tag = gumbo_normalize_svg_tagname(&(elem->original_tag));
        if (tag == NULL) tag_name = lookup_standard_tag(doc, pd, elem->tag);
        else tag_name = xmlDictLookup(doc->dict, BAD_CAST tag, elem->original_tag.length);
    } else tag_name = lookup_standard_tag(doc, pd, elem->tag);

    if (UNLIKELY(!tag_name)) ABORT;

    // Must use xmlNewDocNodeEatName as we are using a dict string and without this
    // if an error occurs and we have to call xmlFreeNode before adding this node to the doc
    // we get a segfault.
    result = xmlNewDocNodeEatName(doc, NULL, (xmlChar*)tag_name, NULL);
    if (UNLIKELY(!result)) ABORT;
    result->line = elem->start_pos.line;
    if (opts->line_number_attr) {
        snprintf(buf, sizeof(buf) - 1, "%u", elem->start_pos.line);
        if (UNLIKELY(!xmlNewNsPropEatName(result, NULL, (xmlChar*)opts->line_number_attr, BAD_CAST buf))) ABORT;
    }

    if (opts->namespace_elements) {
        if (UNLIKELY(parent->type == GUMBO_NODE_DOCUMENT || elem->tag_namespace != parent->v.element.tag_namespace)) {
            // Default namespace has changed
            namespace = xmlNewNs(
                    result, BAD_CAST kLegalXmlns[elem->tag_namespace], NULL);
            if (UNLIKELY(!namespace)) ABORT;
        }
        xmlSetNs(result, namespace ? namespace :xml_parent->ns);
    }

    bool needs_reprocess = false;
    if (UNLIKELY(!create_attributes(doc, result, elem, xml_parent, false, &needs_reprocess))) ABORT;
    if (UNLIKELY(needs_reprocess)) {
        if (UNLIKELY(!create_attributes(doc, result, elem, xml_parent, true, &needs_reprocess))) ABORT;
    }
    if (UNLIKELY(nsprefix)) {
        namespace = xmlSearchNs(doc, result, BAD_CAST nsprefix);
        if (!namespace && xml_parent) namespace = xmlSearchNs(doc, xml_parent, BAD_CAST nsprefix);
        if (namespace) xmlSetNs(result, namespace);
    }
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
            ans = create_element(doc, xml_parent, node->parent, *elem, opts);
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
            pd->errmsg =  ERRMSG("unknown gumbo node type");
            break;
    }
    return ans;
}

static inline xmlDocPtr
alloc_doc(Options *opts) {
    xmlDocPtr doc = xmlNewDoc(BAD_CAST "1.0");
    if (doc) {
        if (!doc->dict) {
            doc->dict = xmlDictCreate();
            if (doc->dict == NULL) {
                xmlFreeDoc(doc);
                doc = NULL;
            }
            opts->line_number_attr = xmlDictLookup(doc->dict, BAD_CAST opts->line_number_attr, -1);
        }
        doc->encoding = xmlStrdup(BAD_CAST "UTF-8");
    }
    return doc;
}

static inline bool
add_root_comments(ParseData *pd, GumboDocument *document, GumboNode *root) {
    GumboVector *root_nodes = &(document->children);
    bool before_root = true;
    for (unsigned int i = 0; i < root_nodes->length; i++) {
        GumboNode *root_node = (GumboNode*)root_nodes->data[i];
        if (root_node == root) { before_root = false; continue; }
        if (root_node->type == GUMBO_NODE_COMMENT) {
            xmlNodePtr comment = xmlNewComment(BAD_CAST root_node->v.text.text);
            if (UNLIKELY(!comment)) { pd->errmsg = ERRMSG("Out of memory allocating comment");  return false; }
            if (UNLIKELY(!(before_root ? xmlAddPrevSibling(pd->root, comment) : xmlAddSibling(pd->root, comment)))) {
                pd->errmsg = ERRMSG("Failed to add sibling to root node");
                xmlFreeNode(comment);
                return false;
            }
        }
    }
    return true;
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
    Stack *stack = Stack_alloc(opts->stack_size);
    if (stack == NULL) return NULL;
    Stack_push(stack, root, NULL);
    doc = alloc_doc(opts);
    if (doc == NULL) ABORT;

    GumboDocument* document = &(output->document->v.document);
    if (opts->keep_doctype && output->document->v.document.has_doctype) {
        if(!xmlCreateIntSubset(doc, BAD_CAST document->name, BAD_CAST document->public_identifier, BAD_CAST document->system_identifier)) ABORT;
    }

    parse_data.maybe_xhtml = opts->gumbo_opts.use_xhtml_rules;
    parse_data.sanitize_names = opts->sanitize_names;
    doc->_private = (void*)&parse_data;
    parse_data.lang_attribute = xmlDictLookup(doc->dict, BAD_CAST "lang", 4);
    if (!parse_data.lang_attribute) ABORT;
    while(stack->length > 0) {
        Stack_pop(stack, &gumbo, &parent);
        child = convert_node(doc, parent, gumbo, &elem, opts);
        if (UNLIKELY(!child)) ABORT;
        if (LIKELY(parent)) {
            if (UNLIKELY(!xmlAddChild(parent, child))) ABORT;
        } else parse_data.root = child;
        if (elem != NULL) {
            if (!push_children(child, elem, stack)) ABORT;
        }

    }
    if (parse_data.maybe_xhtml) {
        // Add xml:lang to the root element if it has lang
        xmlChar *root_lang = xmlGetNsProp(parse_data.root, parse_data.lang_attribute, NULL);
        if (root_lang) {
            ensure_xml_ns(doc, &parse_data, parse_data.root);
            if (parse_data.xml) xmlNewNsPropEatName(parse_data.root, parse_data.xml, (xmlChar*)parse_data.lang_attribute, root_lang);
            xmlFree(root_lang);
        }
    }

    xmlDocSetRootElement(doc, parse_data.root);
    // Add any comments that are outside the root element
    if (!add_root_comments(&parse_data, document, root)) ABORT;
#undef ABORT
end:
    if (doc) doc->_private = NULL;
    Stack_free(stack);
    *errmsg = (char*)parse_data.errmsg;
    if(!ok) { if (parse_data.root) xmlFreeNode(parse_data.root); if (doc) xmlFreeDoc(doc); doc = NULL; }
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
