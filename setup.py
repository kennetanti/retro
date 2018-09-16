from __future__ import with_statement
from __future__ import absolute_import
from distutils.spawn import find_executable
from setuptools import setup, Extension, __version__ as setuptools_version
from setuptools.command.build_ext import build_ext
import subprocess
import sys
import os
import shutil
from io import open

VERSION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), u'VERSION')

if not os.path.exists(os.path.join(os.path.dirname(__file__), u'.git')):
    use_scm_version = False
    shutil.copy(u'VERSION', u'retro/VERSION.txt')
else:

    def version_scheme(version):
        with open(VERSION_PATH) as v:
            version_file = v.read()
        if version.distance:
            version_file += u'.dev%d' % version.distance
        return version_file

    def local_scheme(version):
        v = u''
        if version.distance:
            v = u'+' + version.node
        return v

    use_scm_version = {
        u'write_to': u'retro/VERSION.txt',
        u'version_scheme': version_scheme,
        u'local_scheme': local_scheme
    }


class CMakeBuild(build_ext):
    def run(self):
        suffix = super(CMakeBuild, self).get_ext_filename(u'')
        pyext_suffix = u'-DPYEXT_SUFFIX:STRING=%s' % suffix
        pylib_dir = u''
        if not self.inplace:
            pylib_dir = u'-DPYLIB_DIRECTORY:PATH=%s' % self.build_lib
        if self.debug:
            build_type = u'-DCMAKE_BUILD_TYPE=Debug'
        else:
            build_type = u''
        python_executable = u'-DPYTHON_EXECUTABLE:STRING=%s' % sys.executable
        cmake_exe = find_executable(u'cmake')
        if not cmake_exe:
            try:
                import cmake
            except ImportError:
                import pip
                pip.main([u'install', u'cmake'])
                import cmake
            cmake_exe = os.path.join(cmake.CMAKE_BIN_DIR, u'cmake')
        subprocess.check_call([
            cmake_exe, u'.', u'-G', u'Unix Makefiles', build_type, pyext_suffix,
            pylib_dir, python_executable
        ])
        if self.parallel:
            jobs = u'-j%d' % self.parallel
        else:
            import multiprocessing
            jobs = u'-j%d' % multiprocessing.cpu_count()
        make_exe = find_executable(u'make')
        if not make_exe:
            raise RuntimeError(
                u'Could not find Make executable. Is it installed?')
        subprocess.check_call([make_exe, jobs, u'retro'])


platform_globs = [
    u'*-%s/*' % plat for plat in [
        u'Nes', u'Snes', u'Genesis', u'Atari2600', u'GameBoy', u'Sms', u'GameGear',
        u'PCEngine', u'GbColor', u'GbAdvance'
    ]
]

kwargs = {}
if tuple(int(v) for v in setuptools_version.split(u'.')) >= (24, 2, 0):
    kwargs[u'python_requires'] = u'>=3.5.0'

setup(
    name=u'gym-retro',
    author=u'OpenAI',
    author_email=u'vickipfau@openai.com',
    url=u'https://github.com/openai/retro',
    version=open(VERSION_PATH, u'r').read(),
    license=u'MIT',
    install_requires=[u'gym'],
    ext_modules=[Extension(u'retro._retro', [u'CMakeLists.txt', u'src/*.cpp'])],
    cmdclass={u'build_ext': CMakeBuild},
    packages=[
        u'retro', u'retro.data', u'retro.data.stable', u'retro.data.experimental',
        u'retro.data.contrib', u'retro.scripts', u'retro.import'
    ],
    package_data={
        u'retro': [
            u'cores/*.json', u'cores/*_libretro*', u'VERSION.txt', u'README.md',
            u'LICENSES.md'
        ],
        u'retro.data.stable':
        platform_globs,
        u'retro.data.experimental':
        platform_globs,
        u'retro.data.contrib':
        platform_globs,
    },
    setup_requires=[u'setuptools_scm'],
    use_scm_version=use_scm_version,
    **kwargs)
