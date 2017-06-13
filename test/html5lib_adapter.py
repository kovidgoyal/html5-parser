#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import unittest

from html5_parser import parse

from . import TestCase, XHTML, SVG, MATHML

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

    NAMESPACE_PREFIXES = {XHTML: '', SVG: 'svg ', MATHML: 'math '}

    def serialize_tag(name):
        ns = 'None '
        if name.startswith('{'):
            ns, name = name[1:].rpartition('}')[::2]
            ns = NAMESPACE_PREFIXES.get(ns, ns)
        return '<' + ns + name + '>'

    def serialize_node(node, level=1):
        lines.append('|' + ' ' * level + serialize_tag(node.tag))
        for child in node:
            serialize_node(child, level + 2)

    serialize_node(root)
    return '\n'.join(lines)


class ConstructionTests(TestCase):

    def implementation(self, inner_html, html, expected, errors):
        html = inner_html or html

        if inner_html:
            raise NotImplementedError('TODO: Implement fragment parsing')
        else:
            root = parse(html, namespace_elements=True)

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
