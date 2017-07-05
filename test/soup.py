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
            type('')(root), '<html><head></head><body><p>\n<a>y</a>z<x:x>1</x:x></p></body></html>')
        root = parse('<svg><image>')
        self.ae(type('')(root), '<html><head></head><body><svg><image></image></svg></body></html>')
        root = parse('<p><!-- ---->')
        self.ae(type('')(root), '<html><head></head><body><p><!-- ----></p></body></html>')
        root = parse('<p><i><b>')
        self.ae(type('')(root), '<html><head></head><body><p><i><b></b></i></p></body></html>')

    def test_attr_soup(self):
        root = parse('<p a=1 b=2 c=3><a a=a>')
        self.ae(dict(root.body.p.attrs), {'a': '1', 'b': '2', 'c': '3'})
        self.ae(dict(root.body.p.a.attrs), {'a': 'a'})
        root = parse('<p a=1><svg><image xlink:href="h">')
        self.ae(
            type('')(root),
            '<html><head></head><body>'
            '<p a="1"><svg><image xlink:href="h"></image></svg></p>'
            '</body></html>'
        )
        root = parse('<html xml:lang="en" lang="fr"><p>')
        self.ae(dict(root.attrs), {'xml:lang': 'en', 'lang': 'fr'})
        root = parse('<p><x xmlns:a="b">')
        self.ae(type('')(root), '<html><head></head><body><p><x xmlns:a="b"></x></p></body></html>')
