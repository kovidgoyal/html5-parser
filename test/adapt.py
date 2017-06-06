#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib
import sys

from html5_parser import parse

from __init__ import XML, TestCase

COMMENT = ' A -- comment -'
DOCTYPE = '<!DOCTYPE html>'
HTML = '''
DOCTYPE
<html lang="en" xml:lang="en">
<head><script>a < & " b</script><title>title</title></head>
<body>
<p>A <span>test</span> of text and tail
<p><svg viewbox="v"><image xlink:href="h">
<p xml:lang="de">
</body>
<!--COMMENT-->
</html>
'''.replace('COMMENT', COMMENT).replace('DOCTYPE', DOCTYPE)


class AdaptTest(TestCase):

    def test_etree(self):
        from xml.etree.ElementTree import tostring
        root = parse(HTML, treebuilder='etree')
        self.ae(root.tag, 'html')
        self.ae(root.attrib, {'{%s}lang' % XML: 'en', 'lang': 'en'})
        self.ae(root.find('./head/script').text, 'a < & " b')
        self.ae(root.find('./body')[-1].attrib, {'{%s}lang' % XML: 'de'})
        self.ae(
            tostring(root.find('body').find('p'), method='text').decode('ascii'),
            'A test of text and tail\n')
        # TODO: SVG, XLINK
        if sys.version_info.major > 2:
            self.assertIn('<!--' + COMMENT + '-->', tostring(root).decode('ascii'))

    def test_dom(self):
        root = parse(HTML, treebuilder='dom', namespace_elements=True)
        doc = root.ownerDocument
        self.ae(doc.doctype, DOCTYPE)
        self.ae(root.tagName, 'html')
        self.ae(
            dict(root.attributes.itemsNS()),
            dict([((u'xmlns', u'xmlns'), 'http://www.w3.org/1999/xhtml'),
                  ((u'xmlns', u'xlink'), 'http://www.w3.org/1999/xlink'),
                  ((u'http://www.w3.org/XML/1998/namespace', u'lang'), 'en')]))
        script = doc.getElementsByTagName('script')[0]
        self.ae(script.firstChild.nodeValue, 'a < & " b')
        p = doc.getElementsByTagName('p')[0]
        self.ae(p.toxml(), '<p>A <span>test</span> of text and tail\n</p>')
        p = doc.getElementsByTagName('p')[-1]
        self.ae(
            dict(p.attributes.itemsNS()),
            dict([((u'http://www.w3.org/XML/1998/namespace', u'lang'), 'de')]))
        # TODO: SVG, XLINK
        self.ae(root.lastChild.nodeValue, COMMENT.replace('--', '\u2014'))

    def test_soup(self):
        from html5_parser.soup import set_soup_module
        soups = []
        for soup in 'bs4 BeautifulSoup'.split():
            try:
                soups.append((soup, importlib.import_module(soup)))
            except ImportError:
                pass
        if not soups:
            self.skipTest('No BeautifulSoup module found')
        for soup_name, soup in soups:
            set_soup_module(soup)
            self.do_soup_test(soup_name)

    def do_soup_test(self, soup_name):
        root = parse(HTML, treebuilder='soup')
        soup = root.parent
        if soup_name != 'BeautifulSoup':
            self.ae(DOCTYPE, str(soup.contents[0]))
        self.ae(root.name, 'html')
        self.ae(dict(root.attrs), {'lang': 'en'})
        self.ae(dict(root.body.contents[-1].attrs), {'lang': 'de'})
        self.ae(root.head.script.string, 'a < & " b')
        self.ae(str(root.find('p')), '<p>A <span>test</span> of text and tail\n</p>')
        # TODO: SVG, XLINK
        self.ae(COMMENT, root.contents[-1].string)
