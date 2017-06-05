#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial

from __init__ import TestCase, tostring
from html5_parser import parse

nsparse = partial(parse, namespace_elements=True)
XHTML = "http://www.w3.org/1999/xhtml"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"


class BasicTests(TestCase):

    def test_single_namespace(self):
        root = nsparse('<p>xxx')
        self.ae(
            tostring(root), '<html xmlns="{}"><head/><body><p>xxx</p></body></html>'.format(XHTML))
        for tag in root.iter('*'):
            self.ae(tag.nsmap, {None: XHTML})
            self.assertIsNone(tag.prefix)
            self.ae(tag.tag.rpartition('}')[0][1:], XHTML, 'no namespace for {}'.format(tag.tag))
        self.ae(len(tuple(root.iterdescendants('{%s}p' % XHTML))), 1)

    def test_multiple_namespace(self):
        root = nsparse('<p>xxx<svg a=1><image b=2 xlink:href="xxx"></svg><p>yyy')
        self.ae(len(tuple(root.iterdescendants('{%s}p' % XHTML))), 2)
        self.ae(len(tuple(root.iterdescendants('{%s}svg' % SVG))), 1)
        self.ae(
            tostring(root),
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<head/><body><p>xxx<svg xmlns="http://www.w3.org/2000/svg" a="1">'
            '<image b="2" xlink:href="xxx"/></svg></p><p>yyy</p></body></html>')
        root = nsparse('<p>xxx<svg a=1><image b=2 xlink:href="href"></svg><p id=1>yyy')
        self.ae(root.xpath('//@id'), ['1'])
        self.ae(root.xpath('//@a'), ['1'])
        self.ae(root.xpath('//@b'), ['2'])
        self.ae(root.xpath('//@xlink:href', namespaces={'xlink': XLINK}), ['href'])

    def test_xml_ns(self):
        root = nsparse('<html xml:lang="fr" lang="es"><svg xml:lang="1">xxx', maybe_xhtml=True)
        self.ae(
            tostring(root), '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr"'
            ' lang="es"><head/><body><svg xmlns="http://www.w3.org/2000/svg" xml:lang="1">'
            'xxx</svg></body></html>')
        self.ae(root.xpath('//@lang'), ['es'])
        self.assertIn('{%s}lang' % XML, root.attrib)
        self.ae(root.xpath('//@xml:lang'), ['fr', '1'])
        root = nsparse('<html xml:lang="fr" lang="es"><svg xml:lang="1">xxx')
        self.ae(root.xpath('//@xml:lang'), ['1'])
        self.assertIn('xml:lang', root.attrib)

    def test_xmlns(self):
        root = nsparse('<html><p xmlns:foo="1">xxx')
