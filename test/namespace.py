#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial

from lxml import etree

from . import TestCase, tostring, XHTML, XLINK, SVG, XML
from html5_parser import parse

nsparse = partial(parse, namespace_elements=True)
XPath = partial(etree.XPath, namespaces={'h': XHTML, 'svg': SVG, 'xl': XLINK})


def namespaces(self, parse_function=partial(parse, maybe_xhtml=True), tostring=tostring):
    ae = self.assertEqual
    tostring = partial(tostring, pretty_print=True)

    def match_and_prefix(root, xpath, prefix, err=''):
        matches = XPath(xpath)(root)
        ae(len(matches), 1, err)
        ae(matches[0].prefix, prefix, err)

    markup = ''' <html xmlns="{xhtml}"><head><body id="test"></html> '''.format(xhtml=XHTML)
    root = parse_function(markup)
    ae(
        len(XPath('//h:body[@id="test"]')(root)), 1,
        'Incorrect parsing, parsed markup:\n' + tostring(root))
    match_and_prefix(root, '//h:body[@id="test"]', None)

    markup = '''
    <html xmlns="{xhtml}"><head><body id="test">
    <svg:svg xmlns:svg="{svg}"><svg:image xmlns:xlink="{xlink}" xlink:href="xxx"/></svg:svg>
    '''.format(
        xhtml=XHTML, svg=SVG, xlink=XLINK)
    root = parse_function(markup)
    err = 'Incorrect parsing, parsed markup:\n' + tostring(root)
    match_and_prefix(root, '//h:body[@id="test"]', None, err)
    match_and_prefix(root, '//svg:svg', 'svg', err)
    match_and_prefix(root, '//svg:image[@xl:href]', 'svg', err)

    markup = '''
    <html xmlns="{xhtml}"><head><body id="test">
    <svg xmlns="{svg}" xmlns:xlink="{xlink}" ><image xlink:href="xxx"/></svg>
    '''.format(
        xhtml=XHTML, svg=SVG, xlink=XLINK)
    root = parse_function(markup)
    err = 'Incorrect parsing, parsed markup:\n' + tostring(root)
    match_and_prefix(root, '//h:body[@id="test"]', None, err)
    match_and_prefix(root, '//svg:svg', None, err)
    match_and_prefix(root, '//svg:image[@xl:href]', None, err)

    markup = '<html><body><svg><image xlink:href="xxx"></svg>'
    root = parse_function(markup)
    err = 'Namespaces not created, parsed markup:\n' + tostring(root)
    match_and_prefix(root, '//svg:svg', None, err)
    match_and_prefix(root, '//svg:image[@xl:href]', None, err)
    image = XPath('//svg:image')(root)[0]
    ae(image.nsmap, {'xlink': XLINK, None: SVG})

    root = parse_function('<html id="a"><p><html xmlns:x="y" lang="en"><p>')
    err = 'Multiple HTML tags not handled, parsed markup:\n' + tostring(root)
    match_and_prefix(root, '//h:html', None, err)
    match_and_prefix(root, '//h:html[@lang]', None, err)
    match_and_prefix(root, '//h:html[@id]', None, err)

    markup = (
        '<html><body><ns1:tag1 xmlns:ns1="NS"><ns2:tag2 xmlns:ns2="NS" ns1:id="test"/>'
        '<ns1:tag3 xmlns:ns1="NS2" ns1:id="test"/></ns1:tag1>')
    root = parse_function(markup)
    err = 'Arbitrary namespaces not preserved, parsed markup:\n' + tostring(root)

    def xpath(expr):
        return etree.XPath(expr, namespaces={'ns1': 'NS', 'ns2': 'NS2'})(root)

    ae(len(xpath('//ns1:tag1')), 1, err)
    ae(len(xpath('//ns1:tag2')), 1, err)
    ae(len(xpath('//ns2:tag3')), 1, err)
    ae(len(xpath('//ns1:tag2[@ns1:id="test"]')), 1, err)
    ae(len(xpath('//ns2:tag3[@ns2:id="test"]')), 1, err)
    for tag in root.iter():
        if 'NS' in tag.tag:
            self.assertIn(tag.prefix, 'ns1 ns2'.split())

    markup = '<html xml:lang="en"><body><p lang="de"><p xml:lang="es"><p lang="en" xml:lang="de">'
    root = parse_function(markup)
    err = 'xml:lang not converted to lang, parsed markup:\n' + tostring(root)
    ae(len(root.xpath('//*[@lang="en"]')), 2, err)
    ae(len(root.xpath('//*[@lang="de"]')), 1, err)
    ae(len(root.xpath('//*[@lang="es"]')), 1, err)
    ae(len(XPath('//*[@xml:lang]')(root)), 1, err)


class NamespaceTests(TestCase):

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

    def test_namespaces(self):
        namespaces(self)

    def test_svg(self):
        root = nsparse(
            '<p><sVg viewbOx="1 2 3 4"><animatecOLOR/><image xlink:href="h"/><img src="s"><p>')
        self.ae(
            tostring(root),
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<head/><body><p>'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="1 2 3 4">'
            '<animateColor/><image xlink:href="h"/></svg>'
            '<img src="s"/></p><p/></body></html>')
        markup = '''
        <html xmlns="{xhtml}"><head><body id="test">
        <svg:svg xmlns:svg="{svg}"><svg:image xmlns:xlink="{xlink}" xlink:href="xxx"/></svg:svg>
        '''.format(xhtml=XHTML, svg=SVG, xlink=XLINK)
        root = parse(markup, maybe_xhtml=True)
        self.ae(root[1][0].tag, '{%s}svg' % SVG)

    def test_xml_ns(self):
        root = nsparse('<html xml:lang="fr" lang="es"><svg xml:lang="1">xxx', maybe_xhtml=True)
        self.ae(
            tostring(root), '<html xmlns="http://www.w3.org/1999/xhtml" lang="es"'
            ' xml:lang="es"><head/><body><svg xmlns="http://www.w3.org/2000/svg" lang="1">'
            'xxx</svg></body></html>')
        self.ae(root.xpath('//@lang'), ['es', '1'])
        self.assertIn('{%s}lang' % XML, root.attrib)
        self.ae(root.xpath('//@xml:lang'), ['es'])
        root = nsparse('<html xml:lang="fr" lang="es"><svg xml:lang="1">xxx')
        self.ae(root.xpath('//@lang'), ['es'])

    def test_xmlns(self):
        root = parse('<html><p xmlns:foo="f">xxx<f:moo/>')
        self.ae(tostring(root), '<html><head/><body><p xmlns_foo="f">xxx<f_moo/></p></body></html>')
        root = parse('<p xmlns="x"><p xmlns:="y"><svg xmlns:xlink="xxx">')
        self.ae(
            tostring(root), '<html xmlns:xlink="http://www.w3.org/1999/xlink"><head/>'
            '<body><p/><p><svg/></p></body></html>')
        root = parse("""<p a:a="1" xmlns:a="a">""", maybe_xhtml=True)
        p = root[1][0]
        self.ae(p.attrib, {'{a}a': '1'})

    def test_preserve_namespaces(self):
        xparse = partial(parse, maybe_xhtml=True)
        root = xparse(
            '<html xmlns:a="1" a:x="x"><p xmlns:b="2" id="p"><a:one n="m" a:a="a" b:a="b"/>')
        self.ae(root.nsmap, {None: XHTML, 'a': '1'})
        self.ae(root.attrib, {'{1}x': 'x'})
        p = root[-1][0]
        self.ae(p.tag, '{%s}p' % XHTML)
        self.ae(p.nsmap, {None: XHTML, 'a': '1', 'b': '2'})
        self.ae(p.attrib, {'id': 'p'})
        a = p[0]
        self.ae(a.attrib, {'{1}a': 'a', '{2}a': 'b', 'n': 'm'})
        self.ae(a.tag, '{1}one')
