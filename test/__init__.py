#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import glob
import os
import sys
import unittest

self_path = os.path.abspath(__file__)
sys.path.insert(0,
                os.path.join(
                    os.path.dirname(os.path.dirname(self_path)), 'build'))
sys.path.append(os.path.dirname(glob.glob('build/*/html5_parser')[0]))

try:
    from html5_parser import set_impl

    # First try to load the custom compiled module
    try:
        import html_parser_debug as html_parser
    except ImportError:
        try:
            import html_parser
        except ImportError:
            from html5_parser import html_parser

    set_impl(html_parser)

except Exception:
    import traceback
    traceback.print_exc()
    raise


class TestCase(unittest.TestCase):

    ae = unittest.TestCase.assertEqual
