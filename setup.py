#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import errno
import os
import re
import shlex
import subprocess
import sys
import sysconfig
from collections import namedtuple
from itertools import chain

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
build_dir = os.path.join(base, 'build')
_plat = sys.platform.lower()
isosx = 'darwin' in _plat
iswindows = hasattr(sys, 'getwindowsversion')
is_travis = os.environ.get('TRAVIS') == 'true'
Env = namedtuple('Env', 'cc cflags ldflags linker debug cc_name cc_ver')


def safe_makedirs(path):
    try:
        os.makedirs(path)
    except EnvironmentError as err:
        if err.errno != errno.EEXIST:
            raise


if iswindows:

    def cc_version():
        return 'cl.exe', (0, 0), 'cl'

    def get_sanitize_args(*a):
        return set()

    def init_env(debug=False, sanitize=False, native_optimizations=False):
        cc, ccver, cc_name = cc_version()
        cflags = '/c /nologo /MD /W3 /EHsc /DNDEBUG'.split()
        ldflags = []
        return Env(cc, cflags, ldflags, 'link.exe', debug, cc_name, ccver)
else:

    def cc_version():
        cc = os.environ.get('CC', 'gcc')
        raw = subprocess.check_output(
            [cc, '-dM', '-E', '-'], stdin=open(os.devnull, 'rb'))
        m = re.search(br'^#define __clang__ 1', raw, flags=re.M)
        cc_name = 'gcc' if m is None else 'clang'
        ver = int(
            re.search(br'#define __GNUC__ (\d+)', raw, flags=re.M)
            .group(1)), int(
                re.search(br'#define __GNUC_MINOR__ (\d+)', raw, flags=re.M)
                .group(1))
        return cc, ver, cc_name

    def get_sanitize_args(cc, ccver):
        sanitize_args = set()
        if cc == 'gcc' and ccver < (4, 8):
            return sanitize_args
        sanitize_args.add('-fno-omit-frame-pointer')
        sanitize_args.add('-fsanitize=address')
        if (cc == 'gcc' and ccver >= (5, 0)) or (cc == 'clang' and not isosx):
            # clang on oS X does not support -fsanitize=undefined
            sanitize_args.add('-fsanitize=undefined')
            # if cc == 'gcc' or (cc == 'clang' and ccver >= (4, 2)):
            #     sanitize_args.add('-fno-sanitize-recover=all')
        return sanitize_args

    def init_env(debug=False, sanitize=False, native_optimizations=False):
        native_optimizations = (native_optimizations and not sanitize and
                                not debug)
        cc, ccver, cc_name = cc_version()
        print('CC:', cc, ccver, cc_name)
        stack_protector = '-fstack-protector'
        if ccver >= (4, 9) and cc_name == 'gcc':
            stack_protector += '-strong'
        missing_braces = ''
        if ccver < (5, 2) and cc_name == 'gcc':
            missing_braces = '-Wno-missing-braces'
        optimize = '-ggdb' if debug or sanitize else '-O3'
        sanitize_args = get_sanitize_args(cc_name,
                                          ccver) if sanitize else set()
        cflags = os.environ.get(
            'OVERRIDE_CFLAGS',
            ('-Wextra -Wno-missing-field-initializers -Wall -std=c99'
             ' -pedantic-errors -Werror {} {} -D{}DEBUG -fwrapv {} {} -pipe {}'
             ).format(optimize, ' '.join(sanitize_args), (''
                                                          if debug else 'N'),
                      stack_protector, missing_braces, '-march=native'
                      if native_optimizations else ''))
        cflags = shlex.split(cflags) + shlex.split(
            sysconfig.get_config_var('CCSHARED'))
        ldflags = os.environ.get('OVERRIDE_LDFLAGS',
                                 '-Wall ' + ' '.join(sanitize_args) +
                                 ('' if debug else ' -O3'))
        ldflags = shlex.split(ldflags)
        cflags += shlex.split(os.environ.get('CFLAGS', ''))
        ldflags += shlex.split(os.environ.get('LDFLAGS', ''))
        cflags.append('-pthread')
        return Env(cc, cflags, ldflags, cc, debug, cc_name, ccver)


def define(x):
    return '-D' + x


def run_tool(cmd):
    if hasattr(cmd, 'lower'):
        cmd = shlex.split(cmd)
    print(' '.join(cmd))
    p = subprocess.Popen(cmd)
    ret = p.wait()
    if ret != 0:
        raise SystemExit(ret)


def newer(dest, *sources):
    try:
        dtime = os.path.getmtime(dest)
    except EnvironmentError:
        return True
    for s in chain(sources, (self_path,)):
        if os.path.getmtime(s) >= dtime:
            return True
    return False


def option_parser():
    p = argparse.ArgumentParser()
    p.add_argument(
        'action',
        nargs='?',
        default='build',
        choices='build test'.split(),
        help='Action to perform (default is build)')
    return p


def find_c_files(src_dir):
    ans, headers = [], []
    for x in os.listdir(src_dir):
        ext = os.path.splitext(x)[1]
        if ext == '.c':
            ans.append(os.path.join(src_dir, x))
        elif ext == '.h':
            headers.append(os.path.join(src_dir, x))
    ans.sort(key=os.path.getmtime, reverse=True)
    return tuple(ans), tuple(headers)


def build_obj(src, env, headers):
    suffix = '-debug' if env.debug else ''
    obj = os.path.join(
        'build', os.path.basename(src).rpartition('.')[0] + suffix + '.o')
    if not newer(obj, src, *headers):
        return
    if iswindows:
        cmd = [env.cc] + env.cflags + ['/Tc' + src] + ['/Fo' + obj]
    else:
        cmd = [env.cc] + env.cflags + ['-c', src] + ['-o', obj]
    run_tool(cmd)
    return obj


def build(args):
    objects, debug_objects = [], []
    for sdir in ('gumbo',):
        sources, headers = find_c_files(sdir)
        if not iswindows:
            env = init_env(debug=True, sanitize=True)
            debug_objects.extend(build_obj(c, env, headers) for c in sources)
        env = init_env()
        objects.extend(build_obj(c, env, headers) for c in sources)


def main():
    args = option_parser().parse_args()
    os.chdir(base)
    safe_makedirs(build_dir)
    if args.action == 'build':
        build(args)
    elif args.action == 'test':
        os.execlp(sys.executable, sys.executable, os.path.join(
            base, 'test.py'))


if __name__ == '__main__':
    main()
