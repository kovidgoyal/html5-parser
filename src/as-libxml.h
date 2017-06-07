/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

#pragma once

#include <libxml/tree.h>

#include "data-types.h"

xmlDocPtr create_doc(void);

xmlNodePtr convert_tree(xmlDocPtr doc, GumboNode *root, Options *opts, char **errmsg);
