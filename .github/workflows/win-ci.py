#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import print_function

import errno
import glob
import io
import os
import pipes
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

ZLIB = "http://zlib.net/zlib-{}.tar.xz".format("1.2.11")
LIBXML2 = "ftp://xmlsoft.org/libxml2/libxml2-{}.tar.gz".format('2.9.4')
LIBXSLT = "ftp://xmlsoft.org/libxml2/libxslt-{}.tar.gz".format('1.1.28')
LXML = "https://pypi.python.org/packages/20/b3/9f245de14b7696e2d2a386c0b09032a2ff6625270761d6543827e667d8de/lxml-3.8.0.tar.gz"  # noqa
SW = os.path.abspath('sw')
if 'PY' in os.environ and 'Platform' in os.environ:
    PYTHON = os.path.expandvars('C:\\Python%PY%-%Platform%\\python.exe').replace('-x86', '')
else:
    PYTHON = sys.executable
os.environ['SW'] = SW
os.environ['PYTHONPATH'] = os.path.expandvars('%SW%\\python\\Lib\\site-packages;%PYTHONPATH%')


def printf(*a, **k):
    print(*a, **k)
    sys.stdout.flush()


def walk(path='.'):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            yield os.path.join(dirpath, f)


def download_file(url):
    for i in range(5):
        try:
            printf('Downloading', url)
            try:
                return subprocess.check_output(['curl.exe', '-fSL', url])
            except FileNotFoundError:
                try:
                    from urllib.request import urlopen
                except ImportError:
                    from urllib import urlopen
                return urlopen(url).read()
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise SystemExit('Failed to download: {}'.format(url))


def split(x):
    x = x.replace('\\', '\\\\')
    return shlex.split(x)


def run(*args, env=None, cwd=None):
    if len(args) == 1 and isinstance(args[0], type('')):
        cmd = split(args[0])
    else:
        cmd = args
    printf(' '.join(pipes.quote(x) for x in cmd))
    sys.stdout.flush()
    if env:
        printf('Using modified env:', env)
        e = os.environ.copy()
        e.update(env)
        env = e
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env)
    except EnvironmentError as err:
        if err.errno == errno.ENOENT:
            raise SystemExit('Could not find the program: %s' % cmd[0])
        raise
    if p.wait() != 0:
        raise SystemExit(p.returncode)


def download_and_extract(url):
    raw = io.BytesIO(download_file(url))
    with tarfile.open(fileobj=raw, mode='r:*') as f:
        f.extractall()
    for x in os.listdir('.'):
        if os.path.isdir(x):
            os.chdir(x)
            return


def ensure_dir(path):
    try:
        os.makedirs(path)
    except EnvironmentError as err:
        if err.errno != errno.EEXIST:
            raise


def replace_in_file(path, old, new, missing_ok=False):
    if isinstance(old, type('')):
        old = old.encode('utf-8')
    if isinstance(new, type('')):
        new = new.encode('utf-8')
    with open(path, 'r+b') as f:
        raw = f.read()
        if isinstance(old, bytes):
            nraw = raw.replace(old, new)
        else:
            nraw = old.sub(new, raw)
        if raw == nraw and not missing_ok:
            raise ValueError('Failed (pattern not found) to patch: ' + path)
        f.seek(0), f.truncate()
        f.write(nraw)


def copy_headers(pattern, destdir='include'):
    dest = os.path.join(SW, destdir)
    ensure_dir(dest)
    files = glob.glob(pattern)
    for f in files:
        dst = os.path.join(dest, os.path.basename(f))
        if os.path.isdir(f):
            shutil.copytree(f, dst)
        else:
            shutil.copy2(f, dst)


def install_binaries(pattern, destdir='lib', fname_map=os.path.basename):
    dest = os.path.join(SW, destdir)
    ensure_dir(dest)
    files = glob.glob(pattern)
    files.sort(key=len, reverse=True)
    if not files:
        raise ValueError('The pattern %s did not match any actual files' % pattern)
    for f in files:
        dst = os.path.join(dest, fname_map(f))
        shutil.copy(f, dst)
        os.chmod(dst, 0o755)
        if os.path.exists(f + '.manifest'):
            shutil.copy(f + '.manifest', dst + '.manifest')


def install_tree(src, dest_parent='include', ignore=None):
    dest_parent = os.path.join(SW, dest_parent)
    dst = os.path.join(dest_parent, os.path.basename(src))
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    return dst


def pure_python():
    run(PYTHON, '-m', 'pip', 'install', 'chardet', 'bs4', '--prefix', os.path.join(SW, 'python'))
    run(PYTHON, '-c', 'import bs4; print(bs4)')


def zlib():
    run('nmake -f win32/Makefile.msc')
    install_binaries('zlib1.dll*', 'bin')
    install_binaries('zlib.lib'), install_binaries('zdll.*')
    copy_headers('zconf.h'), copy_headers('zlib.h')


def libxml2():
    run(
        *(
            'cscript.exe configure.js include={0}/include lib={0}/lib prefix={0} zlib=yes iconv=no'.
            format(SW.replace(os.sep, '/')).split()),
        cwd='win32')
    run('nmake /f Makefile.msvc', cwd='win32')
    install_tree('include/libxml', 'include/libxml2')
    for f in walk('.'):
        if f.endswith('.dll'):
            install_binaries(f, 'bin')
        elif f.endswith('.lib'):
            install_binaries(f)


def libxslt():
    run(
        *(
            'cscript.exe configure.js include={0}/include include={0}/include/libxml2 lib={0}/lib '
            'prefix={0} zlib=yes iconv=no'.format(SW.replace(os.sep, '/')).split()),
        cwd='win32')
    replace_in_file('libxslt/win32config.h', '#define snprintf _snprintf', '')
    for f in walk('.'):
        if os.path.basename(f).startswith('Makefile'):
            replace_in_file(f, '/OPT:NOWIN98', '', missing_ok=True)
    run('nmake /f Makefile.msvc', cwd='win32')
    install_tree('libxslt', 'include')
    install_tree('libexslt', 'include')
    for f in walk('.'):
        if f.endswith('.dll'):
            install_binaries(f, 'bin')
        elif f.endswith('.lib'):
            install_binaries(f)


def lxml():
    replace_in_file('setupinfo.py', ", 'iconv'", '')
    run(
        PYTHON,
        *(
            'setup.py build_ext -I {0}/include;{0}/include/libxml2 -L {0}/lib'.format(
                SW.replace(os.sep, '/')).split()))
    run(PYTHON, 'setup.py', 'install', '--prefix', os.path.join(SW, 'python'))


def install_deps():
    print(PYTHON)
    for x in 'build lib bin include python/Lib/site-packages'.split():
        ensure_dir(os.path.join(SW, x))
    os.chdir(os.path.join(SW, 'build'))
    base = os.getcwd()
    pure_python()
    for name in 'zlib libxml2 libxslt lxml'.split():
        os.chdir(base)
        if os.path.exists(name):
            continue
        os.mkdir(name), os.chdir(name)
        try:
            download_and_extract(globals()[name.upper()])
            globals()[name]()
        except:
            os.chdir(base)
            shutil.rmtree(name)
            raise


def build():
    p = os.environ['PATH']
    p = os.path.join(SW, 'bin') + os.pathsep + p
    env = dict(
        LIBXML_INCLUDE_DIRS=r'{0}\include;{0}\include\libxml2'.format(SW),
        LIBXML_LIB_DIRS=r'{0}\lib'.format(SW),
        PATH=p
    )
    run(PYTHON, 'setup.py', 'test', env=env)


def main():
    if sys.argv[-1] == 'install_deps':
        install_deps()
    else:
        build()


if __name__ == '__main__':
    main()
