#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import textwrap
from functools import partial

import html5_parser
import html5lib
from bs4 import BeautifulSoup

try:
    from time import monotonic
except ImportError:
    from time import time as monotonic

TF = 'test/large.html'
try:
    raw = open(TF, 'rb').read()
except Exception:
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib import urlopen
    print('Downloading large HTML file...')
    raw = urlopen('https://www.w3.org/TR/html5/single-page.html').read()
    open(TF, 'wb').write(raw)

print('Testing with HTML file of', '{:,}'.format(len(raw)), 'bytes')


def timeit(func, number=1):
    total = 0
    for i in range(number):
        st = monotonic()
        r = func()
        t = monotonic() - st
        total += t
        del r
    return total / number


def doit(name, func, num=20):
    print('Parsing', num, 'times with', name)
    t = timeit(func, num)
    print(name, 'took an average of: {:,.3f} seconds to parse it'.format(t))
    return t


p = argparse.ArgumentParser(description='Benchmark html5-parser')
p.add_argument('treebuilder', nargs='?', default='lxml', choices='lxml soup dom etree'.split())
p.add_argument(
    '--num',
    '-n',
    default=10,
    type=int,
    help='Number of repetitions for html5lib (html5-parser will use 10x as many reps)')
args = p.parse_args()

base_time = doit(
    'html5-parser',
    partial(
        html5_parser.parse,
        raw,
        transport_encoding="utf-8",
        namespace_elements=True,
        treebuilder=args.treebuilder),
    num=args.num * 10)
soup_time = doit(
    'html5-parser-to-soup',
    partial(html5_parser.parse, raw, transport_encoding="utf-8", treebuilder='soup'),
    num=args.num)

h5time = doit(
    'html5lib',
    partial(html5lib.parse, raw, transport_encoding="utf-8", treebuilder=args.treebuilder),
    num=args.num)
soup5_time = doit(
    'BeautifulSoup-with-html5lib', partial(BeautifulSoup, raw, 'html5lib'), num=args.num)
soup4_time = doit('BeautifulSoup-with-lxml', partial(BeautifulSoup, raw, 'lxml'), num=args.num)


def row(*args):
    for a in args:
        print('{:18s}'.format(str(a)), end='|')
    print()


print()
print(textwrap.fill(
    'Results are below. They show how much faster html5-parser is than'
    ' each specified parser. Note that there are two additional considerations:'
    ' what the final tree is and whether the parsing supports the HTML 5'
    ' parsing algorithm. The most apples-to-apples comparison is when the'
    ' final tree is lxml and HTML 5 parsing is supported by the parser being compared to.'
    ' Note that in this case, we have the largest speedup. In all other cases,'
    ' speedup is less because of the overhead of building the final tree'
    ' in python instead of C or because the compared parser does not use'
    ' the HTML 5 parsing algorithm or both.'))
print()
row('Parser', 'Tree', 'Supports HTML 5', 'Speedup (factor)')
print('=' * 79)
row('html5lib', 'lxml', 'yes', round(h5time / base_time))
row('soup+html5lib', 'BeautifulSoup', 'yes', round(soup5_time / soup_time))
row('soup+lxml.html', 'BeautifulSoup', 'no', round(soup4_time / soup_time))
