#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import unittest

from lxml.etree import _Comment
from html5_parser import parse

from . import MATHML, SVG, XHTML, XLINK, XML, TestCase

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
html5lib_tests_path = os.path.join(base, 'html5lib-tests')


class TestData(object):

    def __init__(self, filename):
        with open(filename, 'rb') as f:
            self.lines = f.read().decode('utf-8').splitlines()

    def __iter__(self):
        data = {}
        key = None
        for line in self.lines:
            heading = self.is_section_heading(line)
            if heading:
                if data and heading == 'data':
                    yield self.normalize(data)
                    data = {}
                key = heading
                data[key] = ''
            elif key is not None:
                data[key] += line + '\n'
        if data:
            yield self.normalize(data)

    def is_section_heading(self, line):
        """If the current heading is a test section heading return the heading,
        otherwise return False"""
        if line.startswith("#"):
            return line[1:].strip()
        else:
            return False

    def normalize(self, data):
        return {k: v.rstrip('\n') for k, v in data.items()}


def serialize_construction_output(root):
    tree = root.getroottree()
    lines = []
    if tree.docinfo.doctype:
        lines.append('| ' + tree.docinfo.doctype)

    NAMESPACE_PREFIXES = {XHTML: '', SVG: 'svg ', MATHML: 'math ', XLINK: 'xlink ', XML: 'xml '}

    def add(level, *a):
        lines.append('|' + ' ' * level + ''.join(a))

    def serialize_tag(name, level):
        ns = 'None '
        if name.startswith('{'):
            ns, name = name[1:].rpartition('}')[::2]
            ns = NAMESPACE_PREFIXES.get(ns, ns)
        add(level, '<', ns, name, '>')

    def serialize_attr(name, val, level):
        ns = ''
        if name.startswith('{'):
            ns, name = name[1:].rpartition('}')[::2]
            ns = NAMESPACE_PREFIXES.get(ns, ns)
        level += 2
        add(level, ns, name, '=', '"', val, '"')

    def serialize_text(text, level):
        level += 2
        add(level, '"', text, '"')

    def serialize_comment(node, level=1):
        add(level, '<!-- ', node.text, ' -->')

    def serialize_node(node, level=1):
        serialize_tag(node.tag, level)
        for attr in sorted(node.keys()):
            serialize_attr(attr, node.get(attr), level)
        if node.text:
            serialize_text(node.text, level)
        for child in node:
            if isinstance(child, _Comment):
                serialize_comment(child, level + 2)
            else:
                serialize_node(child, level + 2)
            if child.tail:
                serialize_text(child.tail, level)

    for c in root.itersiblings(preceding=True):
        serialize_comment(c)
    serialize_node(root)
    for c in root.itersiblings():
        serialize_comment(c)
    return '\n'.join(lines)


class ConstructionTests(TestCase):

    def implementation(self, inner_html, html, expected, errors):
        html = inner_html or html
        noscript = re.search(r'^\| +<noscript>$', expected, flags=re.MULTILINE)
        if noscript is not None:
            raise unittest.SkipTest('<noscript> is always parsed with scripting off by gumbo')
        if expected[2:].startswith('<!DOCTYPE html "-//W3C//DTD HTML 4.01//EN" "">'):
            raise unittest.SkipTest('Cannot be bothered with parsing of malformed DOCTYPE')
        for line in errors:
            if 'expected-doctype-' in line or 'unknown-doctype' in line:
                raise unittest.SkipTest('gumbo auto-corrects malformed doctypes')

        if inner_html:
            raise unittest.SkipTest('TODO: Implement fragment parsing')
        else:
            root = parse(html, namespace_elements=True, sanitize_names=False)

        output = serialize_construction_output(root)

        # html5lib doesn't yet support the template tag, but it appears in the
        # tests with the expectation that the template contents will be under the
        # word 'contents', so we need to reformat that string a bit.
        # expected = reformatTemplateContents(expected)

        error_msg = '\n'.join(['\n\nInput:', html, '\nExpected:', expected, '\nReceived:', output])
        self.ae(expected, output, error_msg + '\n')
        # TODO: Check error messages, when there's full error support.

    @classmethod
    def add_single(cls, test_name, num, test):

        def test_func(
            self,
            inner_html=test.get('document-fragment'),
            html=test.get('data'),
            expected=test.get('document'),
            errors=test.get('errors', '').split('\n')
        ):
            return self.implementation(inner_html, html, expected, errors)

        test_func.__name__ = str('test_%s_%d' % (test_name, num))
        setattr(cls, test_func.__name__, test_func)


def html5lib_construction_test_files():
    if os.path.exists(html5lib_tests_path):
        base = os.path.join(html5lib_tests_path, 'tree-construction')
        for x in os.listdir(base):
            if x.endswith('.dat'):
                yield os.path.join(base, x)


def find_tests():
    for ct in html5lib_construction_test_files():
        test_name = os.path.basename(ct).rpartition('.')[0]
        for i, test in enumerate(TestData(ct)):
            ConstructionTests.add_single(test_name, i + 1, test)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConstructionTests)
    return suite
