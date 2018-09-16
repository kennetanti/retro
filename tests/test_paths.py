from __future__ import absolute_import
import retro
import os
import pytest


@pytest.yield_fixture
def custom_cleanup():
    retro.data.Integrations.clear_custom_paths()
    assert not retro.data.Integrations.CUSTOM_ONLY.paths

    yield

    retro.data.Integrations.clear_custom_paths()
    assert not retro.data.Integrations.CUSTOM_ONLY.paths


def test_basic_paths():
    assert retro.data.Integrations.STABLE.paths == [u'stable']
    assert retro.data.Integrations.CONTRIB_ONLY.paths == [u'contrib']
    assert retro.data.Integrations.EXPERIMENTAL_ONLY.paths == [u'experimental']
    assert not retro.data.Integrations.CUSTOM_ONLY.paths

    assert retro.data.Integrations.CONTRIB.paths == [u'contrib', u'stable']
    assert retro.data.Integrations.EXPERIMENTAL.paths == [
        u'experimental', u'stable'
    ]
    assert retro.data.Integrations.CUSTOM.paths == [u'stable']

    assert retro.data.Integrations.ALL.paths == [
        u'contrib', u'experimental', u'stable'
    ]


def test_custom_path(custom_cleanup):
    assert not retro.data.Integrations.CUSTOM_ONLY.paths
    assert retro.data.Integrations.CUSTOM.paths == [u'stable']

    retro.data.Integrations.add_custom_path(u'a')
    assert retro.data.Integrations.CUSTOM_ONLY.paths == [u'a']
    assert retro.data.Integrations.CUSTOM.paths == [u'a', u'stable']

    retro.data.Integrations.add_custom_path(u'b')
    assert retro.data.Integrations.CUSTOM_ONLY.paths == [u'a', u'b']
    assert retro.data.Integrations.CUSTOM.paths == [u'a', u'b', u'stable']


def test_custom_path_default(custom_cleanup):
    assert not retro.data.Integrations.CUSTOM_ONLY.paths
    assert retro.data.Integrations.CUSTOM.paths == [u'stable']
    assert retro.data.Integrations.DEFAULT.paths == [u'stable']

    retro.data.add_custom_integration(u'a')
    assert retro.data.Integrations.CUSTOM_ONLY.paths == [u'a']
    assert retro.data.Integrations.CUSTOM.paths == [u'a', u'stable']
    assert retro.data.Integrations.DEFAULT.paths == [u'a', u'stable']

    retro.data.DefaultIntegrations.reset()
    assert retro.data.Integrations.CUSTOM_ONLY.paths == [u'a']
    assert retro.data.Integrations.CUSTOM.paths == [u'a', u'stable']
    assert retro.data.Integrations.DEFAULT.paths == [u'stable']


def test_custom_path_absolute(custom_cleanup):
    assert not retro.data.get_file_path(
        u'',
        u'Dekadence-Dekadrive.md',
        inttype=retro.data.Integrations.CUSTOM_ONLY)

    test_rom_dir = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), u'roms')
    retro.data.Integrations.add_custom_path(test_rom_dir)
    assert retro.data.get_file_path(u'', u'Dekadence-Dekadrive.md', inttype=retro.data.Integrations.CUSTOM_ONLY) == \
     os.path.join(test_rom_dir, u'Dekadence-Dekadrive.md')


def test_custom_path_relative(custom_cleanup):
    assert not retro.data.get_file_path(
        u'Airstriker-Genesis',
        u'rom.md',
        inttype=retro.data.Integrations.CUSTOM_ONLY)

    retro.data.Integrations.add_custom_path(
        retro.data.Integrations.STABLE.paths[0])
    assert retro.data.get_file_path(u'Airstriker-Genesis', u'rom.md', inttype=retro.data.Integrations.CUSTOM_ONLY) == \
     retro.data.get_file_path(u'Airstriker-Genesis', u'rom.md', inttype=retro.data.Integrations.STABLE)
