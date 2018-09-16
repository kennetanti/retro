#!/usr/bin/env python
from __future__ import with_statement
from __future__ import absolute_import
import getpass
import io
import os
import requests
import retro.data
import subprocess
import sys
import tarfile
import tempfile
import zipfile


def main():
    username = raw_input(u'Steam Username: ')
    password = getpass.getpass(u'Steam Password (leave blank if cached): ')

    if password:
        password = password + u'\n'

        authcode = raw_input(u'Steam Guard code: ')
        if authcode:
            password = password + authcode + u'\n'
        else:
            password = password + u'\r\n'
    else:
        password = u'\r\n'

    with tempfile.TemporaryDirectory() as dir:
        if sys.platform.startswith(u'linux'):
            r = requests.get(
                u'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz'
            )
            steamcmd = u'steamcmd.sh'
        elif sys.platform.startswith(u'darwin'):
            r = requests.get(
                u'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz'
            )
            steamcmd = u'steamcmd.sh'
        elif sys.platform.startswith(u'win'):
            r = requests.get(
                u'https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip'
            )
            steamcmd = u'steamcmd.exe'
        else:
            raise RuntimeError(u'Unknown platform %s' % sys.platform)
        if sys.platform.startswith(u'win'):
            zipf = zipfile.ZipFile(io.BytesIO(r.content))
            zipf.extractall(dir)
        else:
            tarball = tarfile.open(fileobj=io.BytesIO(r.content))
            tarball.extractall(dir)

        # Steamcmd doesn't like to be used as the target of
        # force_install_dir, and will instead install in the
        # default steam directory
        with tempfile.TemporaryDirectory() as rom_install_dir:
            command = [
                os.path.join(
                    dir, steamcmd), u'+login', username, u'+force_install_dir',
                rom_install_dir, u'+@sSteamCmdForcePlatformType', u'windows',
                u'+app_update', u'34270', u'validate', u'+quit'
            ]

            print u'Downloading games...'
            output = subprocess.run(
                command,
                input=password.encode(u'utf-8'),
                stdout=subprocess.PIPE)
            if output.returncode not in (0, 7):
                stdout = output.stdout.decode(u'utf-8').split(u'\n')
                print u'\n'.join([unicode(*stdout[-3:-1])])
                sys.exit(1)
            roms = []
            print u'Installing games...'
            for base, _, files in os.walk(rom_install_dir):
                if not base.endswith(u'uncompressed ROMs'):
                    continue
                roms.extend([os.path.join(base, file) for file in files])
            retro.data.merge(*roms, quiet=False)


if __name__ == u'__main__':
    main()
