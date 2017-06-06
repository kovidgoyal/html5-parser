#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from __init__ import TestCase
from html5_parser import parse

HTML = '''
<html lang="en" xml:lang="en">
<head><script>a < & " b</script><title>title</title></head>
<body>
<p>A <span>test</span> of text and tail
<p><svg viewbox="v"><image xlink:href="h">
</body>
<!-- A -- comment --->
</html>
'''


class AdaptTest(TestCase):

    def test_etree(self):
        from xml.etree.ElementTree import tostring
        root = parse(HTML, treebuilder='etree')
        self.ae(root.tag, 'html')
        self.ae(root.attrib, {'xml:lang': 'en', 'lang': 'en'})
        self.ae(root.find('./head/script').text, 'a < & " b')
        self.ae(
            tostring(root.find('body').find('p'), method='text').decode('ascii'),
            'A test of text and tail\n')
        if sys.version_info.major > 2:
            self.assertIn('<!-- A -- comment --->', tostring(root).decode('ascii'))
