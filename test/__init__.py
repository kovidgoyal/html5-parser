#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import glob
import os
import sys
import unittest

self_path = os.path.abspath(__file__)
base = os.path.dirname(os.path.dirname(self_path))
if 'ASAN_OPTIONS' in os.environ:
    ipath = os.path.join(base, 'build')
else:
    ipath = os.path.dirname(glob.glob('build/*/html5_parser')[0])
sys.path.insert(0, ipath)


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
