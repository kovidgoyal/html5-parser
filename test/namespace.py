#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial

from lxml import etree

from __init__ import TestCase
from html5_parser import parse

nsparse = partial(parse, namespace_elements=True)
XHTML = "http://www.w3.org/1999/xhtml"


class BasicTests(TestCase):

    def test_namespace(self):
        root = nsparse('<p>xxx')
        self.ae(
            etree.tostring(root, encoding='unicode'),
            '<html xmlns="{}"><head/><body><p>xxx</p></body></html>'.format(XHTML))
        for tag in root.iter('*'):
            self.ae(tag.nsmap, {None: XHTML})
            self.assertIsNone(tag.prefix)
            self.ae(tag.tag.rpartition('}')[0][1:], XHTML, 'no namespace for {}'.format(tag.tag))
        self.ae(len(tuple(root.iterdescendants('{%s}p' % XHTML))), 1)
