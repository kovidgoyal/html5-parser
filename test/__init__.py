#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

from lxml import etree

XHTML = "http://www.w3.org/1999/xhtml"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"
MATHML = "http://www.w3.org/1998/Math/MathML"


def tostring(root, **kw):
    kw['encoding'] = kw.get('encoding', 'unicode')
    return etree.tostring(root, **kw)


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
    longMessage = True
    tb_locals = True
    maxDiff = None
