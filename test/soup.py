#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from html5_parser.soup import parse

from . import TestCase


class SoupTest(TestCase):

    def test_simple_soup(self):
        root = parse('<p>\n<a>y</a>z<x:x>1</x:x>')
        self.ae(
            type('')(root), '<html><head></head><body><p>\n<a>y</a>z<x_x>1</x_x></p></body></html>')
        root = parse('<svg><image>')
        self.ae(
            type('')(root), '<html><head></head><body><svg><image></image></svg></body></html>')
        root = parse('<p><!-- ---->')
        self.ae(
            type('')(root), '<html><head></head><body><p><!-- ----></p></body></html>')
        root = parse('<p><i><b>')
        self.ae(
            type('')(root), '<html><head></head><body><p><i><b></b></i></p></body></html>')
