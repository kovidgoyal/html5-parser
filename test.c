/*
 * test.c
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */

#include <Python.h>

int 
main(int argc, char **argv) {
#if PY_MAJOR_VERSION >= 3
    wchar_t *argw[1024] = {0};
    int i;
    for (i = 0; i < argc; i++) {
        argw[i] = (wchar_t*)calloc(sizeof(wchar_t), 1024);
        swprintf(argw[i], 1024, L"%hs", argv[i]);
    }
    return Py_Main(argc, argw);
#else
    return Py_Main(argc, argv);
#endif
}
