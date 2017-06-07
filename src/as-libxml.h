/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

#pragma once

#include "data-types.h"

typedef void libxml_doc;

libxml_doc* copy_libxml_doc(libxml_doc* doc);
libxml_doc free_libxml_doc(libxml_doc* doc);
int get_libxml_version(void);
libxml_doc* convert_gumbo_tree_to_libxml_tree(GumboOutput *output, Options *opts, char **errmsg);
