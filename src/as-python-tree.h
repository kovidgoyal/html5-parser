/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */

#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "data-types.h"
#include "../gumbo/gumbo.h"

PyObject*
as_python_tree(GumboOutput *gumbo_output, Options *opts, PyObject *new_tag, PyObject *new_comment, PyObject *new_string, PyObject *append);
bool
set_known_tag_names(PyObject *val, PyObject*);
