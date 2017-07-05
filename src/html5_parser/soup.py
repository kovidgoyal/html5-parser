#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals


def soup_module():
    if soup_module.ans is None:
        try:
            import bs4
            soup_module.ans = bs4
        except ImportError:
            import BeautifulSoup as bs3
            soup_module.ans = bs3
    return soup_module.ans


soup_module.ans = None


def set_soup_module(val):
    soup_module.ans = val


def bs4_new_tag(Tag, soup):

    def new_tag(name, attrs):
        return Tag(soup, name=name, attrs=attrs)

    return new_tag


def bs3_new_tag(Tag, soup):

    def new_tag(name, attrs):
        ans = Tag(soup, name)
        ans.attrs = attrs.items()
        ans.attrMap = attrs
        return ans

    return new_tag


def init_soup():
    bs = soup_module()
    if bs.__version__.startswith('3.'):
        soup = bs.BeautifulSoup()
        new_tag = bs3_new_tag(bs.Tag, soup)
    else:
        soup = bs.BeautifulSoup('', 'lxml')
        new_tag = bs4_new_tag(bs.Tag, soup)
    Comment = bs.Comment
    return bs, soup, new_tag, Comment


def parse(utf8_data, stack_size=16 * 1024, keep_doctype=False, return_root=True):
    from . import html_parser
    bs, soup, new_tag, Comment = init_soup()
    if not isinstance(utf8_data, bytes):
        utf8_data = utf8_data.encode('utf-8')

    def add_doctype(name, public_id, system_id):
        public_id = (' PUBLIC ' + public_id + ' ') if public_id else ''
        system_id = (' ' + system_id) if system_id else ''
        soup.append(bs.Doctype('<!DOCTYPE {}{}{}>'.format(name, public_id, system_id)))

    dt = add_doctype if keep_doctype and hasattr(bs, 'Doctype') else None
    root = html_parser.parse_and_build(utf8_data, new_tag, Comment, dt, stack_size)
    soup.append(root)
    return root if return_root else soup
