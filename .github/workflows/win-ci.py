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
LXML = "https://files.pythonhosted.org/packages/c5/2f/a0d8aa3eee6d53d5723d89e1fc32eee11e76801b424e30b55c7aa6302b01/lxml-4.6.1.tar.gz"  # noqa
SW = os.path.abspath('sw')
PYTHON = os.path.abspath(sys.executable)
os.environ['SW'] = SW
plat = 'amd64' if sys.maxsize > 2**32 else 'x86'


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


def distutils_vcvars():
    from distutils.msvc9compiler import find_vcvarsall, get_build_version
    return find_vcvarsall(get_build_version())


def remove_dups(variable):
    old_list = variable.split(os.pathsep)
    new_list = []
    for i in old_list:
        if i not in new_list:
            new_list.append(i)
    return os.pathsep.join(new_list)


def query_process(cmd):
    if plat == 'amd64' and 'PROGRAMFILES(x86)' not in os.environ:
        os.environ['PROGRAMFILES(x86)'] = os.environ['PROGRAMFILES'] + ' (x86)'
    result = {}
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    try:
        stdout, stderr = popen.communicate()
        if popen.wait() != 0:
            raise RuntimeError(stderr.decode("mbcs"))

        stdout = stdout.decode("mbcs")
        for line in stdout.splitlines():
            if '=' not in line:
                continue
            line = line.strip()
            key, value = line.split('=', 1)
            key = key.lower()
            if key == 'path':
                if value.endswith(os.pathsep):
                    value = value[:-1]
                value = remove_dups(value)
            result[key] = value

    finally:
        popen.stdout.close()
        popen.stderr.close()
    return result


def query_vcvarsall():
    vcvarsall = distutils_vcvars()
    return query_process('"%s" %s & set' % (vcvarsall, plat))


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
    env = query_vcvarsall()
    os.environ.update(env)
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
        except Exception:
            os.chdir(base)
            shutil.rmtree(name)
            raise


def build():
    env = query_vcvarsall()
    os.environ.update(env)
    os.environ.update(dict(
        LIBXML_INCLUDE_DIRS=r'{0}\include;{0}\include\libxml2'.format(SW),
        LIBXML_LIB_DIRS=r'{0}\lib'.format(SW),
        HTML5_PARSER_DLL_DIR=os.path.join(SW, 'bin'),
        HTML5_PYTHONPATH=os.path.join(SW, 'python', 'Lib', 'site-packages')
    ))
    run(PYTHON, 'setup.py', 'test')


def main():
    if sys.argv[-1] == 'install':
        install_deps()
    else:
        build()


if __name__ == '__main__':
    main()
