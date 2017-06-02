#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from lxml import etree

from __init__ import TestCase, html_parser


class BasicTests(TestCase):

    def test_lxml_integration(self):
        capsule = html_parser.parse(b'<p>xxx')
        root = etree.adopt_external_document(capsule).getroot()
        self.ae(list(root.iterchildren('body')), list(root.xpath('./body')))
        self.ae(root.find('body/p').text, 'xxx')
