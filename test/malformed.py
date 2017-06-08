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
