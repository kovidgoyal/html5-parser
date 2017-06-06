#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import unittest

from lxml import etree

# python 2 inserts the current directory into the path which causes
# import of html5_parser to use the source directory instead of the build
# directory
sys.path = list(filter(None, sys.path))

XHTML = "http://www.w3.org/1999/xhtml"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"


def tostring(root):
    return etree.tostring(root, encoding='unicode')


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
    longMessage = True
    tb_locals = True
