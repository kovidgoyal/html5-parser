#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from lxml import etree

from __init__ import TestCase, html_parser
from html5_parser import parse


class BasicTests(TestCase):

    def test_lxml_integration(self):
        capsule = html_parser.parse(b'<p>xxx')
        root = etree.adopt_external_document(capsule).getroot()
        self.ae(list(root.iterchildren('body')), list(root.xpath('./body')))
        self.ae(root.find('body/p').text, 'xxx')
        # Test that lxml is not copying the doc internally
        root.set('attr', 'abc')
        cap2 = html_parser.clone_doc(capsule)
        root2 = etree.adopt_external_document(cap2).getroot()
        self.ae(etree.tostring(root), etree.tostring(root2))

    def test_stack(self):
        sz = 100
        raw = '\n'.join(['<p>{}'.format(i) for i in range(sz)])
        for stack_size in (3, 4, 5, 8000):
            r = parse(raw, stack_size=stack_size)
            self.ae(len(tuple(r.iterdescendants('p'))), sz)
