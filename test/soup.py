#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import gc

from html5_parser.soup import parse, is_bs3

from . import TestCase


def collect():
    for i in range(3):
        gc.collect()


class SoupTest(TestCase):

    def test_simple_soup(self):
        root = parse('<p>\n<a>y</a>z<x:x>1</x:x>')
        self.ae(
            type('')(root), '<html><head></head><body><p>\n<a>y</a>z<x:x>1</x:x></p></body></html>')
        root = parse('<svg><image>')
        self.ae(type('')(root), '<html><head></head><body><svg><image/></svg></body></html>')
        root = parse('<p><!-- ---->')
        self.ae(type('')(root), '<html><head></head><body><p><!-- ----></p></body></html>')
        root = parse('<p><i><b>')
        self.ae(type('')(root), '<html><head></head><body><p><i><b></b></i></p></body></html>')
        root = parse('<p>a<br>b')
        self.ae(type('')(root), '<html><head></head><body><p>a<br/>b</p></body></html>')

    def test_attr_soup(self):
        root = parse('<p a=1 b=2 ID=3><a a=a>')
        self.ae(dict(root.body.p.attrs), {'a': '1', 'b': '2', 'id': '3'})
        self.ae(dict(root.body.p.a.attrs), {'a': 'a'})
        self.ae(type('')(root.find(name='a', a='a')), '<a a="a"></a>')
        root = parse('<p a=1><svg><image xlink:href="h">')
        self.ae(
            type('')(root),
            '<html><head></head><body>'
            '<p a="1"><svg><image xlink:href="h"/></svg></p>'
            '</body></html>'
        )
        root = parse('<html xml:lang="en" lang="fr"><p>')
        self.ae(dict(root.attrs), {'xml:lang': 'en', 'lang': 'fr'})
        root = parse('<p><x xmlns:a="b">')
        self.ae(type('')(root), '<html><head></head><body><p><x xmlns:a="b"></x></p></body></html>')

    def test_soup_list_attrs(self):
        if is_bs3():
            self.skipTest('No bs4 module found')
        root = parse('<a class="a b" rel="x y">')
        self.ae(root.body.a.attrs, {'class': 'a b'.split(), 'rel': 'x y'.split()})

    def test_soup_leak(self):
        HTML = '<p a=1>\n<a b=2 id=3>y</a>z<x:x class=4>1</x:x>'
        parse(HTML)  # So that BS and html_parser set up any internal objects

        def do_parse(num):
            collect()
            before = len(gc.get_objects())
            for i in range(num):
                parse(HTML)
            collect()
            return len(gc.get_objects()) - before

        for num in (1, 10, 100):
            self.assertLess(do_parse(num), 2)
