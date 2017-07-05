#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from lxml.etree import _Comment

try:
    dict_items = dict.iteritems
except AttributeError:
    dict_items = dict.items


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


def attrs_iter(elem):
    rmap = None
    for name, val in elem.items():
        if name.startswith('{'):
            uri, _, name = name[1:].rpartition('}')
            if rmap is None:
                rmap = {v: k for k, v in dict_items(elem.nsmap) or {}}
            prefix = rmap.get(uri)
            if prefix:
                name = prefix + ':' + name
        yield name, val


def convert_element(elem, new_tag):
    ans = new_tag(elem.tag, attrs_iter(elem))
    if elem.text:
        ans.append(elem.text)
    return ans


def bs4_new_tag(Tag, soup):

    def nt(name, attrs=None):
        return Tag(soup, name=name, attrs=attrs)

    return nt


def bs3_new_tag(Tag, soup):

    def nt(name, attrs=None):
        ans = Tag(soup, name)
        ans.attrs = None if attrs is None else list(attrs)
        return ans

    return nt


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


def adapt(src_tree, return_root=True, **kw):
    bs, soup, new_tag, Comment = init_soup()
    if src_tree.docinfo.doctype and hasattr(bs, 'Doctype'):
        soup.append(bs.Doctype(src_tree.docinfo.doctype))
    src_root = src_tree.getroot()
    dest_root = convert_element(src_root, new_tag)
    soup.append(dest_root)
    stack = [(src_root, dest_root)]
    while stack:
        src, dest = stack.pop()
        for child in src.iterchildren():
            if isinstance(child, _Comment):
                dchild = Comment(child.text or '')
            else:
                dchild = convert_element(child, new_tag)
                stack.append((child, dchild))
            dest.append(dchild)
            if child.tail:
                dest.append(child.tail)

    return dest_root if return_root else soup


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
