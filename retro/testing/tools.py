from __future__ import with_statement
from __future__ import absolute_import
import glob
import hashlib
import json
import os
import re

import retro.data
from io import open


def load_whitelist(game, inttype):
    try:
        with open(
                retro.data.get_file_path(
                    game, u'metadata.json',
                    inttype | retro.data.Integrations.STABLE)) as f:
            whitelist = json.load(f).get(u'whitelist', {})
    except json.JSONDecodeError:
        return None, [(metadata_file, u'fail decode')]
    except IOError:
        return None, [(metadata_file, u'fail I/O')]
    return whitelist, []


def scan_missing():
    missing = []
    for game in retro.data.list_games(retro.data.Integrations.ALL):
        if not retro.data.get_file_path(game, u'data.json',
                                        retro.data.Integrations.ALL):
            missing.append((game, u'data.json'))
        if not retro.data.get_file_path(game, u'scenario.json',
                                        retro.data.Integrations.ALL):
            missing.append((game, u'scenario.json'))
        if not retro.data.get_file_path(game, u'metadata.json',
                                        retro.data.Integrations.ALL):
            missing.append((game, u'metadata.json'))
        if not retro.data.list_states(game, retro.data.Integrations.ALL):
            missing.append((game, u'*.state'))
        if not retro.data.get_file_path(game, u'rom.sha',
                                        retro.data.Integrations.ALL):
            missing.append((game, u'rom.sha'))
    return missing


def verify_data(game, inttype, raw=None):
    file = os.path.join(unicode(inttype), game, u'data.json')
    path = retro.data.get_file_path(game, u'data.json', inttype)
    if not path:
        return [], []
    try:
        if not raw:
            with open(path) as f:
                data = json.load(f)
        else:
            data = json.loads(raw)
    except json.JSONDecodeError:
        return [], [(file, u'fail decode')]
    except IOError:
        return [], [(file, u'fail I/O')]

    whitelist, errors = load_whitelist(game, inttype)
    if errors:
        return [], errors
    warnings = []

    data = data.get(u'info')
    if not data:
        return [], [(file, u'missing info')]
    for variable, definition in data.items():
        if u'address' not in definition:
            errors.append((file, u'missing address for %s' % variable))
        if u'type' not in definition:
            errors.append((file, u'missing type for %s' % variable))
        else:
            if not re.match(ur'\|[dinu]1|(>[<=]?|<[>=]?|=[><]?)[dinu][2-8]',
                            definition[u'type']):
                errors.append((
                    file,
                    u'invalid type %s for %s' % (definition[u'type'], variable)))
            elif re.match(
                    ur'([><=]{2}|=[><]|<[>=]|>[<=])[dinu][2-8]|[><=]{1,2}d[5-8]',
                    definition[u'type']):
                warnings.append((file, u'suspicious type %s for %s' %
                                 (definition[u'type'], variable)))
    if u'lives' in data and data[u'lives'].get(u'type', u'') not in (u'|u1', u'|i1',
                                                                 u'|d1'):
        warnings.append(
            (file, u'suspicious type %s for lives' % data[u'lives'][u'type']))
    if u'score' in data and (data[u'score'].get(u'type', u'??')[1:] in (u'u1', u'd1',
                                                                    u'n1', u'n2')
                            or u'i' in data[u'score'].get(u'type', u'')):
        warnings.append(
            (file, u'suspicious type %s for score' % data[u'score'][u'type']))

    whitelist = set((file, w) for w in whitelist.get(u'data.json', []))
    all_warnings = set((file, w) for (file, w) in warnings)
    warnings = list(all_warnings - whitelist)
    errors.extend((u'metadata.json', u'missing warning "%s: %s"' % (file, w))
                  for (file, w) in whitelist - all_warnings)
    return warnings, errors


def verify_scenario(game, inttype, scenario=u'scenario', raw=None,
                    dataraw=None):
    file = os.path.join(unicode(inttype), game, u'%s.json' % scenario)
    path = retro.data.get_file_path(game, u'%s.json' % scenario, inttype)
    if not path:
        return [], []
    try:
        if not raw:
            with open(path) as f:
                scen = json.load(f)
        else:
            scen = json.loads(raw)
    except json.JSONDecodeError:
        return [], [(file, u'fail decode')]
    except IOError:
        return [], [(file, u'fail I/O')]

    whitelist, errors = load_whitelist(game, inttype)
    if errors:
        return [], errors
    warnings = []
    if u'rewards' in scen:
        for i, r in enumerate(scen[u'rewards']):
            if u'variables' not in r and u'script' not in r:
                warnings.append((file, u'missing reward in rewards[%d]' % i))
            elif u'variables' in r and u'script' in r:
                warnings.append(
                    (file,
                     u'both variables and script present in rewards[%d]' % i))
        if u'reward' in scen:
            warnings.append((file, u'reward and rewards both present'))
    elif u'reward' not in scen or (u'variables' not in scen[u'reward']
                                  and u'script' not in scen[u'reward']):
        warnings.append((file, u'missing reward'))
    elif u'variables' in scen[u'reward'] and u'script' in scen[u'reward']:
        warnings.append((file, u'both variables and script present in reward'))

    if u'done' not in scen or (u'variables' not in scen[u'done']
                              and u'script' not in scen[u'done']
                              and u'nodes' not in scen[u'done']):
        warnings.append((file, u'missing done'))

    try:
        if not dataraw:
            datafile = retro.data.get_file_path(
                game,
                u'data.json',
                inttype=inttype | retro.data.Integrations.STABLE)
            with open(datafile) as f:
                data = json.load(f)
        else:
            data = json.loads(dataraw)
        data = data.get(u'info')
        reward = scen.get(u'reward')
        done = scen.get(u'done')
        if reward and u'variables' in reward:
            for variable, definition in reward[u'variables'].items():
                if variable not in data:
                    errors.append((file, u'invalid variable %s' % variable))
                if not definition:
                    errors.append((file, u'invalid definition %s' % variable))
                    continue
                if u'reward' not in definition and u'penalty' not in definition:
                    errors.append((file, u'blank reward %s' % variable))
        if done and u'variables' in done:
            if u'score' in done[u'variables']:
                warnings.append(
                    (file, u'suspicious variable in done condition: score'))
            if u'health' in done[u'variables'] and u'lives' in done[
                    u'variables'] and u'condition' not in done:
                warnings.append((file,
                                 u'suspicious done condition: health OR lives'))
            if done.get(u'condition', u'any') == u'all' and (
                    len(done[u'variables']) + len(done.get(u'nodes', {}))) < 2:
                errors.append(
                    (file, u'incorrect done condition all with only 1 check'))
            if done.get(u'condition', u'any') == u'any' and (
                    len(done[u'variables']) + len(done.get(u'nodes', {}))) > 2:
                warnings.append(
                    (file,
                     u'suspicious done condition any with more than 2 checks'))
            for variable, definition in done[u'variables'].items():
                if u'op' not in definition:
                    errors.append((file,
                                   u'invalid done condition %s' % variable))
                elif definition.get(u'reference', 0) == 0:
                    if u'op' in (u'equal', u'negative-equal'):
                        warnings.append(
                            (file, u'incorrect op: zero for %s' % variable))
                    elif u'op' == u'not-equal':
                        warnings.append(
                            (file, u'incorrect op: nonzero for %s' % variable))
                    elif u'op' == u'less-than':
                        warnings.append(
                            (file, u'incorrect op: negative for %s' % variable))
                    elif u'op' == u'greater-than':
                        warnings.append(
                            (file, u'incorrect op: positive for %s' % variable))
                if data:
                    if variable not in data:
                        errors.append((file, u'invalid variable %s' % variable))
                    else:
                        if u'i' not in data[variable].get(
                                u'type', u'') and definition.get(
                                    u'op', u'') == u'negative' and definition.get(
                                        u'measurement') != u'delta':
                            errors.append(
                                (file,
                                 u'op: negative on unsigned %s' % variable))
    except (json.JSONDecodeError, IOError):
        pass

    whitelist = set((file, w) for w in whitelist.get(os.path.split(file)[-1], []))
    all_warnings = set((file, w) for (file, w) in warnings)
    warnings = list(all_warnings - whitelist)
    errors.extend((u'metadata.json', u'missing warning "%s: %s"' % (file, w))
                  for (file, w) in whitelist - all_warnings)
    return warnings, errors


def verify_default_state(game, inttype, raw=None):
    file = os.path.join(unicode(inttype), game, u'metadata.json')
    path = retro.data.get_file_path(game, u'metadata.json', inttype)
    if not path:
        return [], []
    try:
        if not raw:
            with open(path) as f:
                metadata = json.load(f)
        else:
            metadata = json.loads(raw)
    except json.JSONDecodeError:
        return [], [(file, u'fail decode')]
    except IOError:
        return [], []

    errors = []
    state = metadata.get(u'default_state')
    if not state:
        return [], [(file, u'default state missing')]
    if state not in retro.data.list_states(
            game, inttype | retro.data.Integrations.STABLE):
        errors.append((file, u'invalid default state %s' % state))

    return [], errors


def verify_hash_collisions():
    errors = []
    seen_hashes = {}
    for game in retro.data.list_games(retro.data.Integrations.ALL):
        shafile = retro.data.get_file_path(game, u'rom.sha',
                                           retro.data.Integrations.ALL)
        try:
            with open(os.path.join(shafile, u'rom.sha')) as f:
                expected_shas = f.read().strip().split(u'\n')
        except IOError:
            continue
        for expected_sha in expected_shas:
            seen = seen_hashes.get(expected_sha, [])
            seen.append(game)
            seen_hashes[expected_sha] = seen
    for sha, games in seen_hashes.items():
        if len(games) < 2:
            continue
        for game in games:
            errors.append((game, u'sha duplicate'))
    return [], errors


def verify_genesis(game, inttype):
    whitelist, errors = load_whitelist(game, inttype)
    if errors:
        return [], errors
    warnings = []

    rom = retro.data.get_romfile_path(game, inttype=inttype)
    if not rom.endswith(u'.md'):
        errors.append((game, u'invalid extension for %s' % rom))
    if u'rom.md' in whitelist:
        return [], []
    with open(rom, u'rb') as f:
        header = f.read(512)
    if header[0x100:0x105] not in ('SEGA ', ' SEGA'):
        errors.append((game, u'invalid genesis rom'))
    return warnings, errors


def verify_extension(game, inttype):
    whitelist, errors = load_whitelist(game, inttype)
    if errors:
        return [], errors
    warnings = []

    rom = os.path.split(retro.data.get_romfile_path(game, inttype=inttype))[-1]
    platform = retro.data.EMU_EXTENSIONS.get(os.path.splitext(rom)[-1])

    if not platform or not game.endswith(u'-%s' % platform):
        errors.append((game, u'invalid extension for %s' % rom))
    if rom in whitelist:
        return [], []
    return warnings, errors


def verify_rom(game, inttype):
    try:
        rom = retro.data.get_romfile_path(game, inttype=inttype)
    except FileNotFoundError:
        return [], [(game, u'ROM file missing')]

    if game.endswith(u'-Genesis'):
        return verify_genesis(game, inttype)
    return verify_extension(game, inttype)
