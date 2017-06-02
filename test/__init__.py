#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import unittest

iswindows = hasattr(sys, 'getwindowsversion')
self_path = os.path.abspath(__file__)
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(self_path)), 'build'))

if iswindows:
    import html_parser
else:
    import html_parser_debug as html_parser

html_parser


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
