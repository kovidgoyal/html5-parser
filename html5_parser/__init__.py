#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
from collections import namedtuple
from locale import getpreferredencoding

from lxml import etree  # Must be imported before html_parser to initialize libxml

from . import html_parser

version = namedtuple('Version', 'major minor patch')(
    html_parser.MAJOR, html_parser.MINOR, html_parser.PATCH)

if not hasattr(etree, 'adopt_external_document'):
    raise ImportError('Your version of lxml is too old, version 3.8.0 is minimum')

LIBXML_VERSION = ((html_parser.LIBXML_VERSION // 10000) % 100,
                  (html_parser.LIBXML_VERSION // 100) % 100, html_parser.LIBXML_VERSION % 100, )
if LIBXML_VERSION != etree.LIBXML_VERSION:
    raise RuntimeError(
        'html5-parser and lxml are using different versions of libxml2.'
        ' This happens commonly when using pip installed versions of lxml.'
        ' Use pip install --no-binary lxml lxml instead.'
        ' libxml2 versions: html5-parser: {} != lxml: {}'.format(
            LIBXML_VERSION, etree.LIBXML_VERSION))

UTF_8 = 'utf-8'


def check_bom(data):
    q = data[:4]
    if q == codecs.BOM_UTF8:
        return UTF_8
    if q == codecs.BOM_UTF16_BE:
        return 'utf-16-be'
    if q == codecs.BOM_UTF16_LE:
        return 'utf-16-le'
    if q == codecs.BOM_UTF32_BE:
        return 'utf-32-be'
    if q == codecs.BOM_UTF32_LE:
        return 'utf-32-le'


def check_for_meta_charset(raw):
    from .encoding_parser import EncodingParser  # delay load
    q = raw[:1024]
    parser = EncodingParser(q)
    encoding = parser()
    if encoding in ("utf-16", "utf-16-be", "utf-16-le"):
        encoding = "utf-8"
    return encoding


def detect_encoding(raw):
    from chardet import detect  # delay load
    q = raw[:50 * 1024]
    return detect(q)['encoding']


passthrough_encodings = frozenset(('utf-8', 'utf8', 'ascii'))


def safe_get_preferred_encoding():
    try:
        ans = getpreferredencoding(False)
    except Exception:
        pass
    else:
        try:
            return codecs.lookup(ans).name
        except LookupError:
            pass


def as_utf8(bytes_or_unicode, transport_encoding=None, fallback_encoding=None):
    if isinstance(bytes_or_unicode, bytes):
        data = bytes_or_unicode
        if transport_encoding:
            if transport_encoding.lower() not in passthrough_encodings:
                data = bytes_or_unicode.decode(transport_encoding).encode('utf-8')
        else:
            # See
            # https://www.w3.org/TR/2011/WD-html5-20110113/parsing.html#determining-the-character-encoding
            bom = check_bom(data)
            if bom is not None:
                if bom is not UTF_8:
                    data = data.decode(bom).encode('utf-8')
            else:
                encoding = (
                    check_for_meta_charset(data) or detect_encoding(data) or fallback_encoding or
                    safe_get_preferred_encoding() or 'cp-1252')
                if encoding and encoding.lower() not in passthrough_encodings:
                    data = data.decode(encoding).encode('utf-8')
    else:
        data = bytes_or_unicode.encode('utf-8')
    return data


def parse(
    html, transport_encoding=None, fallback_encoding=None, keep_doctype=True, stack_size=16 * 1024
):
    '''
    :param html: The HTML to be parsed. Can be either bytes or a unicode string.
    :param transport_encoding: If specified, assume the passed in bytes are in this encoding.
        Ignored if :param:`html` is unicode.
    :param fallback_encoding: If no encoding could be detected, then use this encoding.
        Defaults to an encoding based on system locale.
    :param keep_doctype: Keep the <DOCTYPE> (if any).
    :param stack_size: The initial size (number of items) in the stack. The
        default is sufficient to avoid memory allocations for all but the
        largest documents.
    '''
    data = as_utf8(html or b'', transport_encoding, fallback_encoding)
    capsule = html_parser.parse(data, keep_doctype=keep_doctype, stack_size=stack_size)
    return etree.adopt_external_document(capsule).getroot()
