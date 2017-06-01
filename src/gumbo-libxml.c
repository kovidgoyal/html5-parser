/*
 * gumbo-libxml.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

// Based on https://github.com/nostrademons/gumbo-libxml/blob/master/gumbo_libxml.c

#include "../gumbo/gumbo.h"

#include <assert.h>
#include <string.h>

#include <libxml/tree.h>

// Namespace constants, indexed by GumboNamespaceEnum.
static const char* kLegalXmlns[] = {
  "http://www.w3.org/1999/xhtml",
  "http://www.w3.org/2000/svg",
  "http://www.w3.org/1998/Math/MathML"
};

static 
xmlNodePtr convert_node(xmlDocPtr doc, GumboNode* node, bool attach_original) {
  xmlNodePtr result = NULL;
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
        xmlNsPtr namespace = NULL;
        result = xmlNewNode(NULL, BAD_CAST gumbo_normalized_tagname(elem->tag));
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
          xmlAddChild(result, convert_node(
              doc, elem->children.data[i], attach_original));
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
  if (attach_original) {
    result->_private = node;
  }
  return result;
}

xmlDocPtr 
gumbo_libxml_parse_with_options(GumboOptions* options, const char* buffer, size_t buffer_length) {
  xmlDocPtr doc = xmlNewDoc(BAD_CAST "1.0");
  GumboOutput* output = gumbo_parse_with_options(options, buffer, buffer_length);
  GumboDocument* doctype = & output->document->v.document;
  xmlCreateIntSubset(
      doc,
      BAD_CAST doctype->name,
      BAD_CAST doctype->public_identifier,
      BAD_CAST doctype->system_identifier);
      
  xmlDocSetRootElement(doc, convert_node(doc, output->root, false));
  gumbo_destroy_output(output);
  return doc;

}

xmlDocPtr 
gumbo_libxml_parse(const char* buffer) {
  GumboOptions options = kGumboDefaultOptions;
  return gumbo_libxml_parse_with_options(&options, buffer, strlen(buffer));
}
