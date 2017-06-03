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


def parse(bytes_or_unicode, keep_doctype=True, stack_size=16 * 1024):
    '''
    :param keep_doctype: Keep the <DOCTYPE> (if any).
    :param stack_size: The initial size (number of items) in the stack. The
        default is sufficient to avoid memory allocations for all but the
        largest documents.
    '''
    capsule = html_parser.parse(
        bytes_or_unicode, keep_doctype=keep_doctype, stack_size=stack_size)
    return etree.adopt_external_document(capsule).getroot()
