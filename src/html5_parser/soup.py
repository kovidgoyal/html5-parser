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


def convert_element(elem, new_tag):
    ans = new_tag(elem.tag)
    if elem.text:
        ans.append(elem.text)
    rmap = None
    for name, val in elem.items():
        if name.startswith('{'):
            uri, _, name = name[1:].rpartition('}')
            if rmap is None:
                rmap = {v: k for k, v in dict_items(elem.nsmap) or {}}
            prefix = rmap.get(uri)
            if prefix:
                name = prefix + ':' + name
        ans[name] = val
    return ans


def adapt(src_tree, return_root=True, **kw):
    bs = soup_module()
    if bs.__version__.startswith('3.'):
        soup = bs.BeautifulSoup()
    else:
        soup = bs.BeautifulSoup('', 'lxml')
    Tag, Comment = bs.Tag, bs.Comment
    if src_tree.docinfo.doctype and hasattr(bs, 'Doctype'):
        soup.append(bs.Doctype(src_tree.docinfo.doctype))
    new_tag = getattr(soup, 'new_tag', None) or (lambda x: Tag(soup, x))
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
