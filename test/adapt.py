#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib
import sys

from html5_parser import parse

from . import SVG, XHTML, XLINK, TestCase

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
        root = parse(HTML, treebuilder='etree', namespace_elements=True)
        self.ae(root.tag, '{%s}html' % XHTML)
        ns = {'h': XHTML, 's': SVG, 'x': XLINK}
        self.ae(root.attrib, {'lang': 'en', 'xml_lang': 'en'})
        self.ae(root.find('./h:head/h:script', ns).text, 'a < & " b')
        self.ae(root.find('./h:body', ns)[-1].attrib, {'xml_lang': 'de'})
        self.ae(
            tostring(root.find('h:body/h:p', ns), method='text').decode('ascii'),
            'A test of text and tail\n')
        svg = root.find('./h:body/h:p/s:svg', ns)
        self.ae(svg.attrib, {'viewBox': 'v'})
        img = svg[0]
        self.ae(img.attrib, {'{%s}href' % XLINK: 'h'})
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
                  ((None, u'xml_lang'), 'en'),
                  ((None, u'lang'), 'en')]))
        script = doc.getElementsByTagName('script')[0]
        self.ae(script.firstChild.nodeValue, 'a < & " b')
        p = doc.getElementsByTagName('p')[0]
        self.ae(p.toxml(), '<p>A <span>test</span> of text and tail\n</p>')
        p = doc.getElementsByTagName('p')[-1]
        self.ae(
            dict(p.attributes.itemsNS()),
            dict([((None, u'xml_lang'), 'de')]))
        svg = doc.getElementsByTagName('svg')[0]
        self.ae(
            dict(svg.attributes.itemsNS()), {(None, 'viewBox'): 'v',
                                             (u'xmlns', u'xmlns'): 'http://www.w3.org/2000/svg'})
        self.ae(dict(svg.firstChild.attributes.itemsNS()), dict([((XLINK, u'href'), 'h')]))
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
        set_soup_module(None)

    def do_soup_test(self, soup_name):
        root = parse(HTML, treebuilder='soup')
        soup = root.parent
        if soup_name != 'BeautifulSoup':
            self.ae(DOCTYPE, str(soup.contents[0]))
        self.ae(root.name, 'html')
        self.ae(dict(root.attrs), {'xml:lang': 'en', 'lang': 'en'})
        self.ae(dict(root.body.contents[-1].attrs), {'xml:lang': 'de'})
        self.ae(root.head.script.string, 'a < & " b')
        self.ae(str(root.find('p')), '<p>A <span>test</span> of text and tail\n</p>')
        svg = root.find('svg')
        self.ae(dict(svg.attrs), {'viewBox': 'v'})
        self.ae(dict(svg.contents[0].attrs), {'xlink:href': 'h'})
        self.ae(COMMENT, root.contents[-1].string)
