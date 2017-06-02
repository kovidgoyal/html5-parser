#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

from lxml import etree

from . import html_parser

version = namedtuple('Version', 'major minor patch')(
    html_parser.MAJOR, html_parser.MINOR, html_parser.PATCH)

if not hasattr(etree, 'adopt_external_document'):
    raise ImportError(
        'Your version of lxml is too old, version 3.8.0 is minimum')

impl = html_parser


def set_impl(x):
    global impl
    impl = x


def parse(bytes_or_unicode, **kwargs):
    capsule = impl.parse(bytes_or_unicode, **kwargs)
    return etree.adopt_external_document(capsule).getroot()
