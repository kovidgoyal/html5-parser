#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import importlib
import os
import sys
import unittest

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
html5lib_tests_path = os.path.join(base, 'test', 'html5lib-tests')


def itertests(suite):
    stack = [suite]
    while stack:
        suite = stack.pop()
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                stack.append(test)
                continue
            if test.__class__.__name__ == 'ModuleImportFailure':
                raise Exception('Failed to import a test module: %s' % test)
            yield test


def filter_tests(suite, test_ok):
    ans = unittest.TestSuite()
    added = set()
    for test in itertests(suite):
        if test_ok(test) and test not in added:
            ans.addTest(test)
            added.add(test)
    return ans


def filter_tests_by_name(suite, name):
    if not name.startswith('test_'):
        name = 'test_' + name
    if name.endswith('_'):
        def q(test):
            return test._testMethodName.startswith(name)
    else:
        def q(test):
            return test._testMethodName == name

    return filter_tests(suite, q)


def filter_tests_by_module(suite, *names):
    names = frozenset(names)

    def q(test):
        m = test.__class__.__module__.rpartition('.')[-1]
        return m in names

    return filter_tests(suite, q)


def find_tests():
    suites = []
    for f in os.listdir(os.path.join(base, 'test')):
        n, ext = os.path.splitext(f)
        if ext == '.py' and n not in ('__init__', 'html5lib_adapter'):
            m = importlib.import_module('test.' + n)
            suite = unittest.defaultTestLoader.loadTestsFromModule(m)
            suites.append(suite)
    if 'SKIP_HTML5LIB' not in os.environ:
        from test.html5lib_adapter import find_tests
        suites.extend(find_tests())
    return unittest.TestSuite(suites)


def run_memleak_tests():
    tests = find_tests()

    tests = filter_tests_by_name(tests, 'asan_memleak')
    r = unittest.TextTestRunner
    result = r(verbosity=4).run(tests)

    if not result.wasSuccessful():
        raise SystemExit(1)


def main():
    sys.path.insert(0, base)
    if 'MEMLEAK_EXE' in os.environ:
        return run_memleak_tests()
    parser = argparse.ArgumentParser(
        description='''\
Run the specified tests, or all tests if none are specified. Tests
can be specified as either the test method name (without the leading test_)
or a module name with a trailing period.
''')
    parser.add_argument(
        'test_name',
        nargs='*',
        help=(
            'Test name (either a method name or a module name with a trailing period)'
            '. Note that if the name ends with a trailing underscore all tests methods'
            ' whose names start with the specified name are run.'
        )
    )
    args = parser.parse_args()

    tests = find_tests()
    suites = []
    for name in args.test_name:
        if name.endswith('.'):
            suites.append(filter_tests_by_module(tests, name[:-1]))
        else:
            suites.append(filter_tests_by_name(tests, name))
    tests = unittest.TestSuite(suites) if suites else tests

    r = unittest.TextTestRunner
    result = r().run(tests)

    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
