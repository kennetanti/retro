#!/usr/bin/env python

from __future__ import absolute_import
import argparse
import retro

parser = argparse.ArgumentParser()
parser.add_argument(u'game', help=u'the name or path for the game to run')
parser.add_argument(
    u'state',
    nargs=u'?',
    help=u'the initial state file to load, minus the extension')
parser.add_argument(
    u'--scenario',
    u'-s',
    default=u'scenario',
    help=u'the scenario file to load, minus the extension')
parser.add_argument(
    u'--record', u'-r', action=u'store_true', help=u'record bk2 movies')
parser.add_argument(
    u'--verbose',
    u'-v',
    action=u'count',
    default=1,
    help=u'increase verbosity (can be specified multiple times)')
parser.add_argument(
    u'--quiet',
    u'-q',
    action=u'count',
    default=0,
    help=u'decrease verbosity (can be specified multiple times)')
parser.add_argument(
    u'--players',
    u'-p',
    type=int,
    default=1,
    help=u'number of players/agents (default: 1)')
args = parser.parse_args()

env = retro.make(
    args.game,
    args.state or retro.State.DEFAULT,
    scenario=args.scenario,
    record=args.record,
    players=args.players)
verbosity = args.verbose - args.quiet
try:
    while True:
        ob = env.reset()
        t = 0
        totrew = [0] * args.players
        while True:
            ac = env.action_space.sample()
            ob, rew, done, info = env.step(ac)
            t += 1
            if t % 10 == 0:
                if verbosity > 1:
                    infostr = u''
                    if info:
                        infostr = u', info: ' + u', '.join(
                            [u'%s=%i' % (k, v) for k, v in info.items()])
                    print (u't=%i' % t) + infostr
                env.render()
            if args.players == 1:
                rew = [rew]
            for i, r in enumerate(rew):
                totrew[i] += r
                if verbosity > 0:
                    if r > 0:
                        print u't=%i p=%i got reward: %g, current reward: %g' %
                              (t, i, r, totrew[i])
                    if r < 0:
                        print u't=%i p=%i got penalty: %g, current reward: %g' %
                              (t, i, r, totrew[i])
            if done:
                env.render()
                try:
                    if verbosity >= 0:
                        if args.players > 1:
                            print u"done! total reward: time=%i, reward=%r" %
                                  (t, totrew)
                        else:
                            print u"done! total reward: time=%i, reward=%d" %
                                  (t, totrew[0])
                        raw_input(u"press enter to continue")
                        print
                    else:
                        raw_input(u"")
                except EOFError:
                    exit(0)
                break
except KeyboardInterrupt:
    exit(0)
