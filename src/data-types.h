/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

#pragma once

#include "../gumbo/gumbo.h"
#include <stdbool.h>

#ifdef _MSC_VER
#define UNUSED 
#define EXPORTED __declspec(dllexport)
#else
#define UNUSED __attribute__ ((unused))
#define EXPORTED __attribute__ ((visibility ("default")))
#endif
#ifdef __builtin_expect
#define LIKELY(x)    __builtin_expect (!!(x), 1)
#define UNLIKELY(x)  __builtin_expect (!!(x), 0)
#else
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#endif

#define MIN(x, y) ((x) < (y) ? (x) : (y))
#define MAX(x, y) ((x) > (y) ? (x) : (y))

typedef struct {
    unsigned int stack_size;
    bool keep_doctype, namespace_elements, sanitize_names;
    const void* line_number_attr;
    GumboOptions gumbo_opts;
} Options;


// We only allow subset of the valid characters defined in the XML spec for
// performance, as the following tests can be run directly on UTF-8 without
// decoding. Also the other characters are never actually used successfully in
// the wild.

#define VALID_FIRST_CHAR(c) ( \
        (c >= 'a' && c <= 'z') || \
        (c >= 'A' && c <= 'Z') || \
        c == '_'\
)

#define VALID_CHAR(c)  ( \
        (c >= 'a' && c <= 'z') || \
        (c >= '0' && c <= '9') || \
        (c == '-') || \
        (c >= 'A' && c <= 'Z') || \
        (c == '_') || (c == '.') \
)

#define STRFY(x) #x
#define STRFY2(x) STRFY(x)
#define ERRMSG(x) ("File: " __FILE__ " Line: " STRFY2(__LINE__) ": " x)
#define NOMEM (ERRMSG("Out of memory"))
