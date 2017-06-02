#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
from distutils.core import Extension, setup
from itertools import chain

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
sys.path.insert(0, base)
if True:
    from build import (
        SRC_DIRS, find_c_files, include_dirs, libraries,
        library_dirs, version
    )
del sys.path[0]

src_files = tuple(chain(*map(lambda x: find_c_files(x)[0], SRC_DIRS)))

setup(
    name='html-parser',
    version='{}.{}.{}'.format(*version),
    author='Kovid Goyal',
    description='Fast C based HTML 5 parsing for python',
    license='Apache 2.0',
    ext_modules=[
        Extension(
            'html_parser',
            include_dirs=include_dirs(),
            libraries=libraries(),
            library_dirs=library_dirs(),
            sources=list(map(str, src_files)))
    ])
