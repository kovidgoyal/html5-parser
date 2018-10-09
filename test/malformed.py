#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from . import TestCase
from html5_parser import parse


class BasicTests(TestCase):

    def test_name_sanitization(self):
        root = parse('<p bad(attr=x><bad:name/>')
        p = root[1][0]
        self.ae(p.attrib, {'bad_attr': 'x'})
        self.ae(p[0].tag, 'bad_name')

    def test_multiple_roots(self):
        root = parse("<html><html />", maybe_xhtml=True)
        from lxml import etree
        self.ae(etree.tostring(root, encoding='unicode'),
                '<html xmlns="http://www.w3.org/1999/xhtml"><head/><body/></html>')
