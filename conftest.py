from __future__ import absolute_import
import pytest
import retro.data

inttypes = {
    u'exp': retro.data.Integrations.EXPERIMENTAL_ONLY,
    u'contrib': retro.data.Integrations.CONTRIB_ONLY,
}


def pytest_collection_modifyitems(items):
    def test(*args, **kwargs):
        print kwargs
        return False

    for item in items:
        if item.originalname in (u'test_load', u'test_rom', u'test_state',
                                 u'test_hash'):
            for key in item.keywords.keys():
                if u'[' + key + u']' not in item.nodeid:
                    continue

                game = key.split(u'_')
                gamename = u'%s-%s' % (game[0], game[1])
                try:
                    retro.data.get_romfile_path(
                        gamename, inttypes[game[2]]
                        if len(game) > 2 else retro.data.Integrations.STABLE)
                except (FileNotFoundError, KeyError):
                    item.add_marker(pytest.mark.skip)
