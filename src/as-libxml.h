/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

#pragma once

#include "data-types.h"
#include <libxml/tree.h>

xmlDocPtr convert_gumbo_tree_to_libxml_tree(GumboOutput *output, Options *opts, char **errmsg);
