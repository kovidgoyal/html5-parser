#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import unittest
from lxml import etree

self_path = os.path.abspath(__file__)
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(self_path)), 'build'))

try:
    import html_parser_debug as html_parser
except ImportError:
    import html_parser

html_parser


def parse(raw, **kw):
    if not isinstance(raw, bytes):
        raw = raw.encode('utf-8')
    capsule = html_parser.parse(raw, **kw)
    return etree.adopt_external_document(capsule).getroot()


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
