/*
 * main.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */

#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <libxml/xmlmemory.h>
#include "src/as-libxml.h"

static inline libxml_doc*
convert_tree(GumboOutput *output, Options *opts) {
    char *errmsg = NULL;
    libxml_doc *doc = NULL;
    doc = convert_gumbo_tree_to_libxml_tree(output, opts, &errmsg);
    return doc;
}


static inline libxml_doc* 
parse_with_options(const char* buffer, size_t buffer_length, Options *opts) {
    GumboOutput *output = NULL;
    libxml_doc* doc = NULL;
    output = gumbo_parse_with_options(&(opts->gumbo_opts), buffer, buffer_length);
    doc = convert_tree(output, opts);
    gumbo_destroy_output(output);
    free_libxml_doc(doc);
    return doc;
}


int main(int UNUSED argc, char UNUSED **argv) {
    char buf[1024*1024] = {0};
    Options opts = {0};
    opts.gumbo_opts = kGumboDefaultOptions;
    opts.stack_size = 16 * 1024;
    opts.gumbo_opts.max_errors = 0;  
    opts.keep_doctype = 1;
    xmlInitParser();
    ssize_t sz = read(STDIN_FILENO, buf, (sizeof(buf) / sizeof(buf[0])) - 1);
    parse_with_options(buf, (size_t)sz, &opts);
    opts.namespace_elements = 1;
    opts.sanitize_names = 1;
    opts.gumbo_opts.use_xhtml_rules = 1;
    parse_with_options(buf, (size_t)sz, &opts);
    xmlCleanupParser();
    return 0;
}
