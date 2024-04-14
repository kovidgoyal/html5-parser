#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import importlib
import sys
from collections import namedtuple
from locale import getpreferredencoding
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal, Optional, Union, overload, reveal_type
    from xml.dom.minidom import Document
    from xml.etree.ElementTree import Element

    from bs4 import BeautifulSoup
    from lxml.etree import _Element as LxmlElement
    from lxml.html import HtmlElement
    ReturnType = Union[LxmlElement, HtmlElement, Element, Document, BeautifulSoup]
else:
    _Element = ReturnType = HtmlElement = Element = Document = BeautifulSoup = None


if not hasattr(sys, 'generating_docs_via_sphinx'):
    from lxml import etree  # Must be imported before html_parser to initialize libxml

    try:
        from . import html_parser  # type: ignore
    except ImportError:
        raise
    else:
        version = namedtuple('Version', 'major minor patch')(
                html_parser.MAJOR, html_parser.MINOR, html_parser.PATCH)  # type: ignore

        if not hasattr(etree, 'adopt_external_document'):
            raise ImportError('Your version of lxml is too old, version 3.8.0 is minimum')

        LIBXML_VERSION = ((html_parser.LIBXML_VERSION // 10000) % 100,
                          (html_parser.LIBXML_VERSION // 100) % 100,
                          html_parser.LIBXML_VERSION % 100, )
        if LIBXML_VERSION[:2] != etree.LIBXML_VERSION[:2]:
            raise RuntimeError(
                'html5-parser and lxml are using different versions of libxml2.'
                ' This happens commonly when using pip installed versions of lxml.'
                ' Use pip install --no-binary lxml lxml instead.'
                ' libxml2 versions: html5-parser: {} != lxml: {}'.format(
                    LIBXML_VERSION, etree.LIBXML_VERSION))

BOMS = (codecs.BOM_UTF8, codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE)


def check_bom(data):
    for bom in BOMS:
        if data.startswith(bom):
            return bom


def check_for_meta_charset(raw):
    from .encoding_parser import EncodingParser  # delay load
    q = raw[:10 * 1024]
    parser = EncodingParser(q)
    encoding = parser()
    if encoding in ("utf-16", "utf-16be", "utf-16le"):
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
                data = data[len(bom):]
                if bom is not codecs.BOM_UTF8:
                    data = data.decode(bom).encode('utf-8')
            else:
                encoding = (
                    check_for_meta_charset(data) or detect_encoding(data) or fallback_encoding or
                    safe_get_preferred_encoding() or 'cp-1252')
                if encoding and encoding.lower() not in passthrough_encodings:
                    if encoding == 'x-user-defined':
                        # https://encoding.spec.whatwg.org/#x-user-defined
                        buf = (b if b <= 0x7F else 0xF780 + b - 0x80 for b in bytearray(data))
                        try:
                            chr = unichr
                        except NameError:
                            pass
                        data = ''.join(map(chr, buf))
                    else:
                        data = data.decode(encoding).encode('utf-8')
    else:
        data = bytes_or_unicode.encode('utf-8')
    return data


def normalize_treebuilder(x):
    if hasattr(x, 'lower'):
        x = x.lower()
    return {'lxml.etree': 'lxml', 'etree': 'stdlib_etree'}.get(x, x)


NAMESPACE_SUPPORTING_BUILDERS = frozenset('lxml stdlib_etree dom lxml_html'.split())

if TYPE_CHECKING:
    @overload
    def parse(
        html: Union[bytes, str], transport_encoding:Optional[str], namespace_elements: bool, treebuilder: Literal['lxml'],
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> LxmlElement: ...

    @overload
    def parse(
        html: Union[bytes, str], transport_encoding:Optional[str], namespace_elements: bool, treebuilder: Literal['lxml_html'],
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> HtmlElement: ...

    @overload
    def parse(
        html: Union[bytes, str], transport_encoding:Optional[str], namespace_elements: bool, treebuilder: Literal['etree'],
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> Element: ...

    @overload
    def parse(
        html: Union[bytes, str], transport_encoding:Optional[str], namespace_elements: bool, treebuilder: Literal['dom'],
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> Document: ...

    @overload
    def parse(
        html: Union[bytes, str], transport_encoding:Optional[str], namespace_elements: bool, treebuilder: Literal['soup'],
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> BeautifulSoup: ...

    @overload
    def parse(  # type:ignore
        html: Union[bytes, str],
        transport_encoding: Optional[str] = ...,
        namespace_elements: bool = ...,
        treebuilder: Literal['lxml'] = ...,
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> LxmlElement: ...


    @overload
    def parse(
        html: Union[bytes, str],
        transport_encoding: Optional[str] = ...,
        namespace_elements: bool = ...,
        treebuilder: Literal['lxml_html'] = ...,
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> HtmlElement: ...

    @overload
    def parse(  # type: ignore
        html: Union[bytes, str],
        transport_encoding: Optional[str] = ...,
        namespace_elements: bool = ...,
        treebuilder: Literal['etree'] = ...,
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> Element: ...

    @overload
    def parse(  # type: ignore
        html: Union[bytes, str],
        transport_encoding: Optional[str] = ...,
        namespace_elements: bool = ...,
        treebuilder: Literal['dom'] = ...,
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> Document: ...

    @overload
    def parse(
        html: Union[bytes, str],
        transport_encoding: Optional[str] = ...,
        namespace_elements: bool = ...,
        treebuilder: Literal['soup'] = ...,
        fallback_encoding: Optional[str] = ...,
        keep_doctype: bool = ...,
        maybe_xhtml: bool = ...,
        return_root: bool = ...,
        line_number_attr:Optional[str] = ...,
        sanitize_names: bool = ...,
        stack_size: int = ...,
        fragment_context: Optional[str] = ...,
    ) -> BeautifulSoup: ...


def parse(
    html: 'Union[bytes, str]',
    transport_encoding: 'Optional[str]' = None,
    namespace_elements: 'bool' = False,
    treebuilder: "Literal['lxml', 'lxml_html', 'etree', 'dom', 'soup']" = 'lxml',
    fallback_encoding: 'Optional[str]' = None,
    keep_doctype: 'bool' = True,
    maybe_xhtml: 'bool' = False,
    return_root: 'bool' = True,
    line_number_attr: 'Optional[str]' = None,
    sanitize_names: 'bool' = True,
    stack_size: 'int' = 16 * 1024,
    fragment_context: 'Optional[str]' = None,
) -> ReturnType:
    '''
    Parse the specified :attr:`html` and return the parsed representation.

    :param html: The HTML to be parsed. Can be either bytes or a unicode string.

    :param transport_encoding: If specified, assume the passed in bytes are in this encoding.
        Ignored if :attr:`html` is unicode.

    :param namespace_elements:
        Add XML namespaces when parsing so that the resulting tree is XHTML.

    :param treebuilder:
        The type of tree to return. Note that only the lxml treebuilder is fast, as all
        other treebuilders are implemented in python, not C. Supported values are:
          * `lxml <https://lxml.de>`_  -- the default, and fastest
          * `lxml_html <https://lxml.de>`_  -- tree of lxml.html.HtmlElement, same speed as lxml
            (new in *0.4.10*)
          * etree (the python stdlib :mod:`xml.etree.ElementTree`)
          * dom (the python stdlib :mod:`xml.dom.minidom`)
          * `soup <https://www.crummy.com/software/BeautifulSoup>`_ -- BeautifulSoup,
            which must be installed or it will raise an :class:`ImportError`

    :param fallback_encoding: If no encoding could be detected, then use this encoding.
        Defaults to an encoding based on system locale.

    :param keep_doctype: Keep the <DOCTYPE> (if any).

    :param maybe_xhtml: Useful when it is unknown if the HTML to be parsed is
        actually XHTML. Changes the HTML 5 parsing algorithm to be more
        suitable for XHTML. In particular handles self-closed CDATA elements.
        So a ``<title/>`` or ``<style/>`` in the HTML will not completely break
        parsing. Also preserves namespaced tags and attributes even for namespaces
        not supported by HTML 5 (this works only with the ``lxml`` and ``lxml_html``
        treebuilders).
        Note that setting this also implicitly sets ``namespace_elements``.

    :param return_root: If True, return the root node of the document, otherwise
        return the tree object for the document.

    :param line_number_attr: The optional name of an attribute used to store the line number
        of every element. If set, this attribute will be added to each element with the
        element's line number.

    :param sanitize_names: Ensure tag and attributes contain only ASCII alphanumeric
        charactes, underscores, hyphens and periods. This ensures that the resulting
        tree is also valid XML. Any characters outside this set are replaced by
        underscores. Note that this is not strictly HTML 5 spec compliant, so turn it
        off if you need strict spec compliance.

    :param stack_size: The initial size (number of items) in the stack. The
        default is sufficient to avoid memory allocations for all but the
        largest documents.

    :param fragment_context: the tag name under which to parse the HTML when the html
        is a fragment. Common choices are ``div`` or ``body``. To use SVG or MATHML tags
        prefix the tag name with ``svg:`` or ``math:`` respectively. Note that currently
        using a non-HTML fragment_context is not supported. New in *0.4.10*.
    '''
    data = as_utf8(html or b'', transport_encoding, fallback_encoding)
    treebuilder = normalize_treebuilder(treebuilder)
    if treebuilder == 'soup':
        from .soup import parse
        return parse(
            data, return_root=return_root, keep_doctype=keep_doctype, stack_size=stack_size)
    if treebuilder not in NAMESPACE_SUPPORTING_BUILDERS:
        namespace_elements = False
    fragment_namespace = html_parser.GUMBO_NAMESPACE_HTML
    if fragment_context:
        fragment_context = fragment_context.lower()
        if ':' in fragment_context:
            ns, fragment_context = fragment_context.split(':', 1)
            fragment_namespace = {
                'svg': html_parser.GUMBO_NAMESPACE_SVG, 'math': html_parser.GUMBO_NAMESPACE_MATHML,
                'html': html_parser.GUMBO_NAMESPACE_HTML
            }[ns]

    capsule = html_parser.parse(
        data,
        namespace_elements=namespace_elements or maybe_xhtml,
        keep_doctype=keep_doctype,
        maybe_xhtml=maybe_xhtml,
        line_number_attr=line_number_attr,
        sanitize_names=sanitize_names,
        stack_size=stack_size,
        fragment_context=fragment_context,
        fragment_namespace=fragment_namespace,
        )

    interpreter = None
    if treebuilder == 'lxml_html':
        from lxml.html import HTMLParser
        interpreter = HTMLParser()
    ans = etree.adopt_external_document(capsule, parser=interpreter)
    if treebuilder in ('lxml', 'lxml_html'):
        return ans.getroot() if return_root else ans
    m = importlib.import_module('html5_parser.' + treebuilder)
    return m.adapt(ans, return_root=return_root)


if TYPE_CHECKING:
    reveal_type(parse('a'))
    reveal_type(parse('a', 'x', True, 'dom'))
    reveal_type(parse('a', 'x', True, 'lxml', fragment_context='x'))
    reveal_type(parse('a', 'x', True, fragment_context='x'))
    reveal_type(parse('a', transport_encoding='xyz', return_root=True, fallback_encoding='moose'))
    reveal_type(parse('a', transport_encoding='x', return_root=False, treebuilder='etree', fragment_context='y'))
