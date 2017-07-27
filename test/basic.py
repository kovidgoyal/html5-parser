#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import codecs

from lxml import etree

from . import TestCase, tostring
from html5_parser import check_for_meta_charset, html_parser, parse, check_bom, BOMS


class BasicTests(TestCase):
    def test_lxml_integration(self):
        capsule = html_parser.parse(b'<p id=1>xxx')
        root = etree.adopt_external_document(capsule).getroot()
        self.ae(list(root.iterchildren('body')), list(root.xpath('./body')))
        self.ae(root.find('body/p').text, 'xxx')
        self.ae(root.xpath('//@id'), ['1'])
        # Test that lxml is not copying the doc internally
        root.set('attr', 'abc')
        cap2 = html_parser.clone_doc(capsule)
        root2 = etree.adopt_external_document(cap2).getroot()
        self.ae(tostring(root), tostring(root2))

    def test_stack(self):
        sz = 100
        raw = '\n'.join(['<p>{}'.format(i) for i in range(sz)])
        for stack_size in (3, 4, 5, 8000):
            r = parse(raw, stack_size=stack_size)
            self.ae(len(tuple(r.iterdescendants('p'))), sz)

    def test_doctype(self):
        base = '\n<html><body><p>xxx</p></body></html>'
        for dt in (
                'html',
                'html PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                '"http://www.w3.org/TR/html4/strict.dtd"'
        ):
            dt = '<!DOCTYPE {}>'.format(dt)
            t = parse(dt + base).getroottree()
            self.ae(dt, t.docinfo.doctype)
            t = parse(dt + base, keep_doctype=False).getroottree()
            self.assertFalse(t.docinfo.doctype)

    def test_check_bom(self):
        for bom in BOMS:
            self.assertIs(bom, check_bom(bom + b'xxx'))

    def test_meta_charset(self):
        def t(html, expected):
            detected = check_for_meta_charset(html.encode('utf-8'))
            self.ae(detected, expected, '{} is not {} in \n{}'.format(detected, expected, html))
            if detected:
                codecs.lookup(detected)
        t('', None)
        t('<html><meta charset=ISO-8859-5>', 'iso-8859-5')
        t('<html><meta a="1" charset="ISO-8859-5" b="2">', 'iso-8859-5')
        t("<meta charset='ISO-8859-2'/>", 'iso-8859-2')
        t('<html><mEta Charset="ISO-8859-5>', None)
        t("<!--<meta charset='ISO-8859-2'>--><meta charset=\"iso-8859-5\" />", 'iso-8859-5')
        t("<meta http-equiv='moo' content='charset=iso-8859-5'>", None)
        t("<meta http-equiv='Content-Type' content='iso-8859-5'>", None)
        t("<meta http-equiv='Content-Type' content='charset=iso-8859-5'>", 'iso-8859-5')
        t("<meta http-equiv='Content-Type' content='xxx charset=iso-8859-5'>", 'iso-8859-5')
        t("<meta http-equiv='Content-Type' content='xxx;charset=iso-8859-5'>", 'iso-8859-5')
        t("<meta http-equiv='Content-Type' content='xxxcharset=iso-8859-5'>", 'iso-8859-5')
        t("<meta http-equiv='Content-Type' content='xxxcharset =\n iso-8859-5'>", 'iso-8859-5')

    def test_maybe_xhtml(self):
        for tag in 'title script style'.split():
            html = '<html><head><{}/></head><body><p>xxx</p></body></html>'.format(tag)
            root = parse(html)
            root = parse(html, maybe_xhtml=True)
            self.ae(len(root[1]), 1)
            html = '<html><head></head><body><{}/><p>xxx</p></body></html>'.format(tag)
            root = parse(html, maybe_xhtml=True)
            self.ae(len(root[1]), 2)
        root = parse('<title/><title>t</title></title></title><link href="h">', maybe_xhtml=True)
        self.ae(
            tostring(root),
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title/>'
            '<title>t</title><link href="h"/></head><body/></html>')

    def test_line_numbers(self):
        root = parse('<html>\n<head>\n<body>\n<p><span>', line_number_attr='ln')
        self.ae(root.sourceline, 1)
        self.ae(int(root.get('ln')), 1)
        self.ae(root[0].sourceline, 2)
        self.ae(root[1].sourceline, 3)
        self.ae(root[1][0].sourceline, 4)
        self.ae(root[1][0][0].sourceline, 4)
        self.ae(root[1][0][0].get('ln'), '4')
