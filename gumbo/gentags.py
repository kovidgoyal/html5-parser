#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os

self_path = os.path.abspath(__file__)
os.chdir(os.path.dirname(self_path))

with open("tag_strings.h", "wb") as tag_strings, \
        open("tag_enum.h", "wb") as tag_enum, \
        open("tag_sizes.h", "wb") as tag_sizes, \
        open('tag.in', 'rb') as tagfile:
    for tag in tagfile:
        tag = tag.decode('utf-8').strip()
        tag_upper = tag.upper().replace('-', '_')
        tag_strings.write(('"%s",\n' % tag).encode('utf-8'))
        tag_enum.write(('GUMBO_TAG_%s,\n' % tag_upper).encode('utf-8'))
        tag_sizes.write(('%d, ' % len(tag)).encode('utf-8'))
    tag_sizes.write(b'\n')
