#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
from distutils.command.build import build as Build
from itertools import chain

from setuptools import Extension, setup

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
sys.path.insert(0, base)
if True:
    from build import (
        SRC_DIRS, find_c_files, include_dirs, libraries, library_dirs, version, iswindows,
        TEST_COMMAND, add_python_path)
del sys.path[0]

src_files = tuple(chain(*map(lambda x: find_c_files(x)[0], SRC_DIRS)))
cargs = ('/O2' if iswindows else '-O3').split()
if not iswindows:
    cargs.extend('-std=c99 -fvisibility=hidden'.split())


class Test(Build):

    description = "run unit tests after in-place build"

    def run(self):
        Build.run(self)
        if self.dry_run:
            self.announce('skipping "test" (dry run)')
            return
        import subprocess
        env = add_python_path(os.environ.copy(), self.build_lib)
        print('\nrunning tests...')
        sys.stdout.flush()
        ret = subprocess.Popen([sys.executable] + TEST_COMMAND, env=env).wait()
        if ret != 0:
            raise SystemExit(ret)


CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: Apache Software License
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Topic :: Text Processing
Topic :: Text Processing :: Markup
Topic :: Text Processing :: Markup :: HTML
Topic :: Text Processing :: Markup :: XML
"""

setup(
    name='html5-parser',
    version='{}.{}.{}'.format(*version),
    author='Kovid Goyal',
    author_email='redacted@acme.com',
    description='Fast C based HTML 5 parsing for python',
    license='Apache 2.0',
    url='https://html5-parser.readthedocs.io',
    download_url=(
        "https://pypi.python.org/packages/source/m/html5-parser/"
        "html5-parser-{}.{}.{}.tar.gz".format(*version)),
    classifiers=[c for c in CLASSIFIERS.split("\n") if c],
    platforms=['any'],
    install_requires=['chardet', 'lxml>=3.8.0'],
    extras_require={'soup': 'beautifulsoup4'},
    packages=['html5_parser'],
    package_dir={'': 'src'},
    cmdclass={'test': Test},
    ext_modules=[
        Extension(
            'html5_parser.html_parser',
            include_dirs=include_dirs(),
            libraries=libraries(),
            library_dirs=library_dirs(),
            extra_compile_args=cargs,
            sources=list(map(str, src_files)))])
