#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function, unicode_literals)

import glob
import os
import shlex
import shutil
import subprocess
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, '.')
if True:
    from unix_build import version
del sys.path[0]

VERSION = '{}.{}.{}'.format(*version)


def red(text):
    return '\033[91;1m' + text + '\033[39;22m'


def green(text):
    return '\033[92;1m' + text + '\033[39;22m'


def run(*cmd):
    if len(cmd) == 1:
        cmd = shlex.split(cmd[0])
    print(green(' '.join(cmd)))
    ret = subprocess.Popen(cmd).wait()
    if ret != 0:
        raise SystemExit(ret)


def build_release():
    for rem in 'dist build'.split():
        os.path.exists(rem) and shutil.rmtree(rem)
    run(sys.executable, '-m', 'build', '-s')


def tag_release():
    run('git push')
    run('git tag -s "v{0}" -m "version-{0}"'.format(VERSION))
    run('git push origin "v{0}"'.format(VERSION))


def upload_release():
    files = list(glob.glob('dist/*'))
    run('twine', 'upload', '--config-file', os.path.join(os.environ['PENV'], 'pypi'), *files)


try:
    raw_input
except NameError:
    raw_input = input


def main():
    if raw_input('Publish version {} [y/n]? '.format(red(VERSION))) != 'y':
        raise SystemExit(1)
    build_release()
    if raw_input(red('Upload') + ' release [y/n]? ') != 'y':
        raise SystemExit(1)
    tag_release()
    upload_release()


if __name__ == '__main__':
    main()
