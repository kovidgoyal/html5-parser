#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from __init__ import TestCase, XML
from html5_parser import parse

COMMENT = ' A -- comment -'
HTML = '''
<html lang="en" xml:lang="en">
<head><script>a < & " b</script><title>title</title></head>
<body>
<p>A <span>test</span> of text and tail
<p><svg viewbox="v"><image xlink:href="h">
<p>
</body>
<!--COMMENT-->
</html>
'''.replace('COMMENT', COMMENT)


class AdaptTest(TestCase):

    def test_etree(self):
        from xml.etree.ElementTree import tostring
        root = parse(HTML, treebuilder='etree')
        self.ae(root.tag, 'html')
        self.ae(root.attrib, {'{%s}lang' % XML: 'en', 'lang': 'en'})
        self.ae(root.find('./head/script').text, 'a < & " b')
        self.ae(
            tostring(root.find('body').find('p'), method='text').decode('ascii'),
            'A test of text and tail\n')
        if sys.version_info.major > 2:
            self.assertIn('<!--' + COMMENT + '-->', tostring(root).decode('ascii'))

    def test_dom(self):
        root = parse(HTML, treebuilder='dom', namespace_elements=True)
        doc = root.ownerDocument
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
        self.ae(root.lastChild.nodeValue, COMMENT.replace('--', '\u2014'))
