#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import subprocess

self_path = os.path.abspath(__file__)
HEADER = '''\
// Do not edit
// Generated from {}.in (see gentags.py)

'''


def generate_tag_headers():
    with open("gumbo/tag_strings.h", "wb") as tag_strings, \
            open("gumbo/tag_enum.h", "wb") as tag_enum, \
            open("gumbo/tag_sizes.h", "wb") as tag_sizes, \
            open('gumbo/tag.in', 'rb') as tagfile:
        for f in (tag_strings, tag_enum, tag_sizes):
            f.write(HEADER.format('tag').encode('utf-8'))
        for tag in tagfile:
            tag = tag.decode('utf-8').strip()
            tag_upper = tag.upper().replace('-', '_')
            tag_strings.write(('"%s",\n' % tag).encode('utf-8'))
            tag_enum.write(('GUMBO_TAG_%s,\n' % tag_upper).encode('utf-8'))
            tag_sizes.write(('%d, ' % len(tag)).encode('utf-8'))
        tag_sizes.write(b'\n')


def generate_tag_perfect_hash(repetitions=200):
    raw = subprocess.check_output(
        'gperf -LANSI-C --ignore-case -H tag_hash -m{} gumbo/tag.in'.format(repetitions).split()
    ).decode('utf-8').splitlines()
    for i, line in enumerate(raw):
        if line.startswith('in_word_set'):
            break
    else:
        raise SystemExit('Failed to find in_word_set()')
    lines = raw[:i - 1]
    del raw[:i - 1]
    raw = '\n'.join(raw)
    wordlist = re.search("wordlist\[\]\s+=\s+{(.*?)}", raw, re.DOTALL)
    if wordlist is None:
        raise SystemExit('Failed to find wordlist')
    wordlist = [w.strip().replace('"', '') for w in wordlist.group(1).split(',')]
    taglist = ["\tGUMBO_TAG_" + (w.upper().replace('-', '_') if w else 'LAST') for w in wordlist]
    processed = '\n'.join(lines) + '\n\n'
    processed += 'static const GumboTag kGumboTagMap[] = {\n%s\n};' % '\n,'.join(taglist)
    processed = re.sub(
        r'.+^tag_hash',
        HEADER.format('tag') + 'static inline unsigned int\ntag_hash',
        processed,
        flags=re.DOTALL | re.MULTILINE)
    with open('gumbo/tag_perf.h', 'wb') as f:
        f.write(processed.encode('utf-8'))
        f.write(b'\n')


def main():
    os.chdir(os.path.dirname(self_path))
    generate_tag_headers()


if __name__ == '__main__':
    main()
    generate_tag_perfect_hash()
