#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

import ctypes.wintypes
import errno
import glob
import io
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from functools import lru_cache

ZLIB = "http://zlib.net/zlib-{}.tar.xz".format("1.3")
LIBXML2 = "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v2.12.0/libxml2-v2.12.0.tar.gz"
LIBXSLT = "https://gitlab.gnome.org/GNOME/libxslt/-/archive/v1.1.39/libxslt-v1.1.39.tar.gz"
LXML = "https://files.pythonhosted.org/packages/30/39/7305428d1c4f28282a4f5bdbef24e0f905d351f34cf351ceb131f5cddf78/lxml-4.9.3.tar.gz"  # noqa
SW = os.path.abspath('sw')
PYTHON = os.path.abspath(sys.executable)
os.environ['SW'] = SW
os.environ['PYTHONPATH'] = os.path.join(SW, r'python\Lib\site-packages')
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
    printf(' '.join(shlex.quote(x) for x in cmd))
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


def remove_dups(variable):
    old_list = variable.split(os.pathsep)
    new_list = []
    for i in old_list:
        if i not in new_list:
            new_list.append(i)
    return os.pathsep.join(new_list)


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


def cmake_build(
    make_args=(), install_args=(),
    append_to_path=None, env=None,
    **kw
):
    make = 'nmake'
    if isinstance(make_args, str):
        make_args = shlex.split(make_args)
    os.makedirs('build', exist_ok=True)
    defs = {
        'CMAKE_BUILD_TYPE': 'RELEASE',
        'CMAKE_SYSTEM_PREFIX_PATH': SW,
        'CMAKE_INSTALL_PREFIX': SW,
    }
    cmd = ['cmake', '-G', "NMake Makefiles"]
    for d, val in kw.items():
        if val is None:
            defs.pop(d, None)
        else:
            defs[d] = val
    for k, v in defs.items():
        cmd.append('-D' + k + '=' + v)
    cmd.append('..')
    env = env or {}
    env['CMAKE_PREFIX_PATH'] = SW
    run(*cmd, cwd='build', env=env)
    make_opts = []
    run(make, *(make_opts + list(make_args)), cwd='build', env=env)
    mi = [make] + list(install_args) + ['install']
    run(*mi, cwd='build')



def libxml2():
    cmake_build(
        LIBXML2_WITH_ICU='OFF', LIBXML2_WITH_PYTHON='OFF', LIBXML2_WITH_TESTS='OFF',
        LIBXML2_WITH_LZMA='OFF', LIBXML2_WITH_THREADS='OFF', LIBXML2_WITH_ICONV='OFF',
    )


def libxslt():
    cmake_build(
        LIBXSLT_WITH_PYTHON='OFF', LIBXML2_INCLUDE_DIR=f'{SW}/include',
    )


def lxml():
    replace_in_file('setupinfo.py', ", 'iconv'", '')
    run(
        PYTHON,
        *(
            'setup.py build_ext -I {0}/include;{0}/include/libxml2 -L {0}/lib'.format(
                SW.replace(os.sep, '/')).split()))
    run(PYTHON, 'setup.py', 'install', '--prefix', os.path.join(SW, 'python'))
    package = glob.glob(os.path.join(SW, 'python', 'lib', 'site-packages', 'lxml-*.egg', 'lxml'))[0]
    os.rename(package, os.path.join(SW, 'python', 'lib', 'site-packages', 'lxml'))


CSIDL_PROGRAM_FILES = 38
CSIDL_PROGRAM_FILESX86 = 42


@lru_cache()
def get_program_files_location(which=CSIDL_PROGRAM_FILESX86):
    SHGFP_TYPE_CURRENT = 0
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(
        0, which, 0, SHGFP_TYPE_CURRENT, buf)
    return buf.value


@lru_cache()
def find_vswhere():
    for which in (CSIDL_PROGRAM_FILESX86, CSIDL_PROGRAM_FILES):
        root = get_program_files_location(which)
        vswhere = os.path.join(root, "Microsoft Visual Studio", "Installer",
                               "vswhere.exe")
        if os.path.exists(vswhere):
            return vswhere
    raise SystemExit('Could not find vswhere.exe')


def get_output(*cmd):
    return subprocess.check_output(cmd, encoding='mbcs', errors='strict')


@lru_cache()
def find_visual_studio():
    path = get_output(
        find_vswhere(),
        "-latest",
        "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property",
        "installationPath",
        "-products",
        "*"
    ).strip()
    return os.path.join(path, "VC", "Auxiliary", "Build")


@lru_cache()
def find_msbuild():
    base_path = get_output(
        find_vswhere(),
        "-latest",
        "-requires", "Microsoft.Component.MSBuild",
        "-property", 'installationPath'
    ).strip()
    return glob(os.path.join(
        base_path, 'MSBuild', '*', 'Bin', 'MSBuild.exe'))[0]


def find_vcvarsall():
    productdir = find_visual_studio()
    vcvarsall = os.path.join(productdir, "vcvarsall.bat")
    if os.path.isfile(vcvarsall):
        return vcvarsall
    raise SystemExit("Unable to find vcvarsall.bat in productdir: " +
                     productdir)


def query_process(cmd, is64bit):
    if is64bit and 'PROGRAMFILES(x86)' not in os.environ:
        os.environ['PROGRAMFILES(x86)'] = get_program_files_location()
    result = {}
    popen = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
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


@lru_cache()
def query_vcvarsall(is64bit=True):
    plat = 'amd64' if is64bit else 'amd64_x86'
    vcvarsall = find_vcvarsall()
    env = query_process(f'"{vcvarsall}" {plat} & set', is64bit)
    pat = re.compile(r'vs(\d+)comntools', re.I)

    comn_tools = {}

    for k in env:
        m = pat.match(k)
        if m is not None:
            comn_tools[k] = int(m.group(1))
    comntools = sorted(comn_tools, key=comn_tools.__getitem__)[-1]


    def g(k):
        try:
            return env[k]
        except KeyError:
            try:
                return env[k.lower()]
            except KeyError:
                for k, v in env.items():
                    print(f'{k}={v}', file=sys.stderr)
                raise

    return {
        k: g(k)
        for k in (
            'PATH LIB INCLUDE LIBPATH WINDOWSSDKDIR'
            f' {comntools} PLATFORM'
            ' UCRTVERSION UNIVERSALCRTSDKDIR VCTOOLSVERSION WINDOWSSDKDIR'
            ' WINDOWSSDKVERSION WINDOWSSDKVERBINPATH WINDOWSSDKBINPATH'
            ' VISUALSTUDIOVERSION VSCMD_ARG_HOST_ARCH VSCMD_ARG_TGT_ARCH'
        ).split()
    }


def install_deps():
    env = query_vcvarsall()
    os.environ.update(env)
    print(PYTHON)
    run(PYTHON, '-m', 'pip', 'install', 'setuptools')
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
    ))
    print('Using PYTHONPATH:', os.environ['PYTHONPATH'])
    run(PYTHON, 'setup.py', 'test')


def main():
    if sys.argv[-1] == 'install':
        install_deps()
    else:
        build()


if __name__ == '__main__':
    main()
