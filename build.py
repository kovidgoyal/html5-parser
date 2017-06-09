#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function, unicode_literals)

import argparse
import errno
import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig
from collections import namedtuple
from copy import deepcopy
from itertools import chain

self_path = os.path.abspath(__file__)
base = os.path.dirname(self_path)
build_dir = os.path.join(base, 'build', 'custom')
freeze_dir = os.path.join(base, 'build', 'html5_parser')
_plat = sys.platform.lower()
isosx = 'darwin' in _plat
iswindows = hasattr(sys, 'getwindowsversion')
is_travis = os.environ.get('TRAVIS') == 'true'
Env = namedtuple('Env', 'cc cflags ldflags linker debug cc_name cc_ver')
PKGCONFIG = os.environ.get('PKGCONFIG_EXE', 'pkg-config')
with open(os.path.join(base, 'src/python-wrapper.c'), 'rb') as f:
    raw = f.read().decode('utf-8')
version = tuple(
    map(
        int, (
            re.search(r'^#define MAJOR (\d+)', raw, flags=re.MULTILINE).group(1), re.search(
                r'^#define MINOR (\d+)', raw, flags=re.MULTILINE).group(1), re.search(
                    r'^#define PATCH (\d+)', raw, flags=re.MULTILINE).group(1), )))


def safe_makedirs(path):
    try:
        os.makedirs(path)
    except EnvironmentError as err:
        if err.errno != errno.EEXIST:
            raise


def add_python_flags(env, return_libs=False):
    env.cflags.extend('-I' + sysconfig.get_path(x) for x in 'include platinclude'.split())
    libs = []
    libs += sysconfig.get_config_var('LIBS').split()
    libs += sysconfig.get_config_var('SYSLIBS').split()
    fw = sysconfig.get_config_var('PYTHONFRAMEWORK')
    if fw:
        for var in 'data include stdlib'.split():
            val = sysconfig.get_path(var)
            if val and '/{}.framework'.format(fw) in val:
                fdir = val[:val.index('/{}.framework'.format(fw))]
                if os.path.isdir(os.path.join(fdir, '{}.framework'.format(fw))):
                    framework_dir = fdir
                    break
        else:
            raise SystemExit('Failed to find Python framework')
        libs.append(os.path.join(framework_dir, sysconfig.get_config_var('LDLIBRARY')))
    else:
        libs += ['-L' + sysconfig.get_config_var('LIBDIR')]
        libs += ['-lpython' + sysconfig.get_config_var('VERSION') + getattr(sys, 'abiflags', '')]
        libs += sysconfig.get_config_var('LINKFORSHARED').split()
    env.ldflags.extend(libs)
    return libs if return_libs else env


def pkg_config(pkg, *args):
    val = subprocess.check_output([PKGCONFIG, pkg] + list(args)).decode('utf-8')
    return list(filter(None, map(str, shlex.split(val))))


def env_var(which, default='', split=os.pathsep):
    val = str(os.environ.get(which, default))
    if not split:
        return val
    return list(filter(None, val.split(split)))


def include_dirs():
    if 'LIBXML_INCLUDE_DIRS' in os.environ:
        return env_var('LIBXML_INCLUDE_DIRS')
    return [x[2:] for x in pkg_config('libxml-2.0', '--cflags-only-I')]


def libraries():
    if iswindows:
        return env_var('LIBXML_LIBS', 'libxml2')
    if 'LIBXML_LIBS' in os.environ:
        return env_var('LIBXML_LIBS')
    return [x[2:] for x in pkg_config('libxml-2.0', '--libs-only-l')]


def library_dirs():
    if 'LIBXML_LIB_DIRS' in os.environ:
        return env_var('LIBXML_LIB_DIRS')
    return [x[2:] for x in pkg_config('libxml-2.0', '--libs-only-L')]


def cc_version():
    cc = os.environ.get('CC', 'gcc')
    raw = subprocess.check_output([cc, '-dM', '-E', '-'], stdin=open(os.devnull, 'rb'))
    m = re.search(br'^#define __clang__ 1', raw, flags=re.M)
    cc_name = 'gcc' if m is None else 'clang'
    ver = int(re.search(br'#define __GNUC__ (\d+)', raw, flags=re.M).group(1)), int(
        re.search(br'#define __GNUC_MINOR__ (\d+)', raw, flags=re.M).group(1))
    return cc, ver, cc_name


def get_sanitize_args(cc, ccver):
    sanitize_args = set()
    if cc == 'gcc' and ccver < (4, 8):
        return sanitize_args
    sanitize_args.add('-fno-omit-frame-pointer')
    sanitize_args.add('-fsanitize=address')
    if (cc == 'gcc' and ccver >= (5, 0)) or (cc == 'clang' and not isosx):
        # clang on macOS does not support -fsanitize=undefined
        sanitize_args.add('-fsanitize=undefined')
        # if cc == 'gcc' or (cc == 'clang' and ccver >= (4, 2)):
        #     sanitize_args.add('-fno-sanitize-recover=all')
    return sanitize_args


def init_env(debug=False, sanitize=False, native_optimizations=False, add_python=True):
    native_optimizations = (native_optimizations and not sanitize and not debug)
    cc, ccver, cc_name = cc_version()
    stack_protector = '-fstack-protector'
    if ccver >= (4, 9) and cc_name == 'gcc':
        stack_protector += '-strong'
    missing_braces = ''
    if ccver < (5, 2) and cc_name == 'gcc':
        missing_braces = '-Wno-missing-braces'
    optimize = '-ggdb' if debug or sanitize else '-O3'
    sanitize_args = get_sanitize_args(cc_name, ccver) if sanitize else set()
    cflags = os.environ.get(
        'OVERRIDE_CFLAGS', (
            '-Wextra -Wno-missing-field-initializers -Wall -std=c99 -fvisibility=hidden'
            ' -pedantic-errors -Werror {} {} -D{}DEBUG -fwrapv {} {} -pipe {}').format(
                optimize, ' '.join(sanitize_args), ('' if debug else 'N'), stack_protector,
                missing_braces, '-march=native' if native_optimizations else ''))
    libxml_cflags = pkg_config('libxml-2.0', '--cflags')
    cflags = shlex.split(cflags) + libxml_cflags + shlex.split(sysconfig.get_config_var('CCSHARED'))
    ldflags = os.environ.get(
        'OVERRIDE_LDFLAGS', '-Wall -shared ' + ' '.join(sanitize_args) + ('' if debug else ' -O3'))
    libxml_ldflags = pkg_config('libxml-2.0', '--libs')
    ldflags = shlex.split(ldflags) + libxml_ldflags
    cflags += shlex.split(os.environ.get('CFLAGS', ''))
    ldflags += shlex.split(os.environ.get('LDFLAGS', ''))
    cflags.append('-pthread')
    ans = Env(cc, cflags, ldflags, cc, debug, cc_name, ccver)
    return add_python_flags(ans) if add_python else ans


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
    for s in chain(sources, (self_path, )):
        if os.path.getmtime(s) >= dtime:
            return True
    return False


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
    obj = os.path.join(build_dir, os.path.basename(src).rpartition('.')[0] + suffix + '.o')
    if newer(obj, src, *headers):
        cflags = list(env.cflags)
        if src.endswith('char_ref.c'):
            cflags.append('-Wno-unused-const-variable')
        cmd = [env.cc] + cflags + ['-c', src] + ['-o', obj]
        run_tool(cmd)
    return obj


TEST_EXE = os.path.join(build_dir, 'test')
if is_travis:
    TEST_EXE = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'test-html5-parser')
SRC_DIRS = 'src gumbo'.split()
MOD_EXT = '.so'


def link(objects, env):
    dest = os.path.join(build_dir, 'html_parser' + MOD_EXT)
    o = ['-o', dest]
    cmd = [env.linker] + objects + o + env.ldflags
    if newer(dest, *objects):
        run_tool(cmd)
    return dest


def build(args):
    debug_objects = []
    debug_env = init_env(debug=True, sanitize=True)
    for sdir in SRC_DIRS:
        sources, headers = find_c_files(sdir)
        if sdir == 'src':
            headers += ('gumbo/gumbo.h', )
        debug_objects.extend(build_obj(c, debug_env, headers) for c in sources)
    link(debug_objects, debug_env)
    ldflags = add_python_flags(deepcopy(debug_env), return_libs=True)
    cmd = ([debug_env.cc] + debug_env.cflags + ['test.c'] + ['-o', TEST_EXE] + ldflags)
    if newer(TEST_EXE, *debug_objects):
        run_tool(cmd)
    for mod in glob.glob(os.path.join(build_dir, '*' + MOD_EXT)):
        shutil.copy2(mod, freeze_dir)
    for mod in glob.glob(os.path.join('src', 'html5_parser', '*.py')):
        shutil.copy2(mod, freeze_dir)


TEST_COMMAND = ['run_tests.py']


def add_python_path(env, path):
    pp = env.get('PYTHONPATH', '')
    to_join = filter(None, [os.path.abspath(path), pp])
    env['PYTHONPATH'] = os.pathsep.join(to_join)
    return env


def option_parser():
    p = argparse.ArgumentParser()
    p.add_argument(
        'action',
        nargs='?',
        default='test',
        choices='build test try'.split(),
        help='Action to perform (default is build)')
    p.add_argument('rest', nargs='*')
    return p


def main():
    args = option_parser().parse_args()
    os.chdir(base)
    safe_makedirs(build_dir), safe_makedirs(freeze_dir)
    if args.action == 'build':
        build(args)
    elif args.action == 'test':
        build(args)
        os.environ['ASAN_OPTIONS'] = 'leak_check_at_exit=0'
        add_python_path(os.environ, os.path.dirname(freeze_dir))
        print('\nrunning tests...')
        os.execlp(TEST_EXE, TEST_EXE, 'run_tests.py', *args.rest)
    elif args.action == 'try':
        build(args)
        os.environ['ASAN_OPTIONS'] = 'leak_check_at_exit=0'
        add_python_path(os.environ, os.path.dirname(freeze_dir))
        os.execlp(
            TEST_EXE, TEST_EXE, '-c', 'from html5_parser import *; ' + args.rest[0], *args.rest[1:])


if __name__ == '__main__':
    main()
