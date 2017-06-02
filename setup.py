#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
from itertools import chain

from setuptools import Extension, setup

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
sys.path.insert(0, base)
if True:
    from build import (
        SRC_DIRS, find_c_files, include_dirs, libraries,
        library_dirs, version, iswindows
    )
del sys.path[0]

src_files = tuple(chain(*map(lambda x: find_c_files(x)[0], SRC_DIRS)))
cargs = ('/O2' if iswindows else '-O3').split()


def discover_tests():
    import unittest
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('test', pattern='*.py')
    return test_suite


setup(
    name='html5-parser',
    version='{}.{}.{}'.format(*version),
    author='Kovid Goyal',
    description='Fast C based HTML 5 parsing for python',
    license='Apache 2.0',
    platforms=['any'],
    # install_requires=['lxml>=3.8.0'],
    packages=['html5_parser'],
    test_suite='setup.discover_tests',
    ext_modules=[
        Extension(
            'html5_parser.html_parser',
            include_dirs=include_dirs(),
            libraries=libraries(),
            library_dirs=library_dirs(),
            extra_compile_args=cargs,
            sources=list(map(str, src_files)))
    ])
