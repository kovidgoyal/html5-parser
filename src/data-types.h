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

typedef struct {
    unsigned int stack_size;
    bool keep_doctype, namespace_elements;
    GumboOptions gumbo_opts;
} Options;
