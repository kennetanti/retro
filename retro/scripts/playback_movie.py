#!/usr/bin/env python
from __future__ import with_statement
from __future__ import division
from __future__ import absolute_import
import argparse
import csv
import json
import numpy as np
import os
import retro
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor as Executor
from itertools import izip
from io import open


def playback_movie(emulator,
                   movie,
                   monitor_csv=None,
                   video_file=None,
                   info_file=None,
                   npy_file=None,
                   viewer=None,
                   video_delay=0,
                   lossless=None,
                   record_audio=True):
    ffmpeg_proc = None
    viewer_proc = None
    info_steps = []
    actions = np.empty(
        shape=(0, emulator.num_buttons * movie.players), dtype=bool)
    if viewer or video_file:
        video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        video.bind((u'127.0.0.1', 0))
        vr = video.getsockname()[1]
        input_vformat = [
            u'-r',
            unicode(emulator.em.get_screen_rate()), u'-s',
            u'%dx%d' % emulator.observation_space.shape[1::-1], u'-pix_fmt',
            u'rgb24', u'-f', u'rawvideo', u'-probesize', u'32',
            u'-thread_queue_size', u'10000', u'-i',
            u'tcp://127.0.0.1:%i?listen' % vr
        ]
        if record_audio:
            audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio.bind((u'127.0.0.1', 0))
            ar = audio.getsockname()[1]
            input_aformat = [
                u'-ar',
                u'%i' % emulator.em.get_audio_rate(), u'-ac', u'2', u'-f', u's16le',
                u'-probesize', u'32', u'-thread_queue_size', u'60', u'-i',
                u'tcp://127.0.0.1:%i?listen' % ar
            ]
        else:
            audio = None
            ar = None
            input_aformat = [u'-an']
        stdout = None
        output = []
        if video_file:
            if not lossless:
                output = [
                    u'-c:a', u'aac', u'-b:a', u'128k', u'-strict', u'-2', u'-c:v',
                    u'libx264', u'-preset', u'slow', u'-crf', u'17', u'-f', u'mp4',
                    u'-pix_fmt', u'yuv420p', video_file
                ]
            elif lossless == u'mp4':
                output = [
                    u'-c:a', u'aac', u'-b:a', u'192k', u'-strict', u'-2', u'-c:v',
                    u'libx264', u'-preset', u'veryslow', u'-crf', u'0', u'-f', u'mp4',
                    u'-pix_fmt', u'yuv444p', video_file
                ]
            elif lossless == u'mp4rgb':
                output = [
                    u'-c:a', u'aac', u'-b:a', u'192k', u'-strict', u'-2', u'-c:v',
                    u'libx264rgb', u'-preset', u'veryslow', u'-crf', u'0', u'-f',
                    u'mp4', u'-pix_fmt', u'rgb24', video_file
                ]
            elif lossless == u'png':
                output = [
                    u'-c:a', u'flac', u'-c:v', u'png', u'-pix_fmt', u'rgb24', u'-f',
                    u'matroska', video_file
                ]
            elif lossless == u'ffv1':
                output = [
                    u'-c:a', u'flac', u'-c:v', u'ffv1', u'-pix_fmt', u'bgr0', u'-f',
                    u'matroska', video_file
                ]
        if viewer:
            stdout = subprocess.PIPE
            output = [u'-c', u'copy', u'-f', u'nut', u'pipe:1']
        ffmpeg_proc = subprocess.Popen(
            [
                u'ffmpeg',
                u'-y',
                *input_vformat,  # Input params (video)
                *input_aformat,  # Input params (audio)
                *output
            ],  # Output params
            stdout=stdout)
        video.close()
        video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if audio:
            audio.close()
            audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        audio_connected = False

        time.sleep(0.3)
        try:
            video.connect((u'127.0.0.1', vr))
        except ConnectionRefusedError:
            video.close()
            if audio:
                audio.close()
            ffmpeg_proc.terminate()
            raise
        if viewer:
            viewer_proc = subprocess.Popen([viewer, u'-'],
                                           stdin=ffmpeg_proc.stdout)
    frames = 0
    score = [0] * movie.players
    reward_fields = [u'r'] if movie.players == 1 else [
        u'r%d' % i for i in xrange(movie.players)
    ]
    wasDone = False

    def killprocs(*args, **kwargs):
        ffmpeg_proc.terminate()
        if viewer:
            viewer_proc.terminate()
            viewer_proc.wait()
        raise BrokenPipeError

    def waitprocs():
        if ffmpeg_proc:
            video.close()
            if audio:
                audio.close()
            if not viewer_proc or viewer_proc.poll() is None:
                ffmpeg_proc.wait()

    while True:
        if movie.step():
            keys = []
            for p in xrange(movie.players):
                for i in xrange(emulator.num_buttons):
                    keys.append(movie.get_key(i, p))
            if npy_file:
                actions = np.vstack((actions, (keys, )))
        elif video_delay < 0 and frames < -video_delay:
            keys = [0] * emulator.num_buttons
        else:
            break
        display, reward, done, info = emulator.step(keys)
        if info_file:
            info_steps.append(info)
        if movie.players > 1:
            for p in xrange(movie.players):
                score[p] += reward[p]
        else:
            score[0] += reward
        frames += 1
        try:
            if hasattr(signal, u'SIGCHLD'):
                signal.signal(signal.SIGCHLD, killprocs)
            if viewer_proc and viewer_proc.poll() is not None:
                break
            if ffmpeg_proc and frames > video_delay:
                video.sendall(str(display))
                if audio:
                    sound = emulator.em.get_audio()
                    if not audio_connected:
                        time.sleep(0.2)
                        audio.connect((u'127.0.0.1', ar))
                        audio_connected = True
                    if len(sound):
                        audio.sendall(str(sound))
        except BrokenPipeError:
            waitprocs()
            raise
        finally:
            if hasattr(signal, u'SIGCHLD'):
                signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        if done and not wasDone:
            if monitor_csv:
                monitor_csv.writerow({
                    **dict(izip(reward_fields, score)), u'l':
                    frames,
                    u't':
                    frames / 60.0
                })
            frames = 0
            score = [0] * movie.players
        wasDone = done
    if hasattr(signal, u'SIGCHLD'):
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    if monitor_csv and frames:
        monitor_csv.writerow({
            **dict(izip(reward_fields, score)), u'l': frames,
            u't': frames / 60.0
        })
    if npy_file:
        kwargs = {u'actions': actions}
        if info_file:
            kwargs[u'info'] = info_steps
        try:
            np.savez_compressed(npy_file, **kwargs)
        except IOError:
            pass
    elif info_file:
        try:
            with open(info_file, u'w') as f:
                json.dump(info_steps, f)
        except IOError:
            pass
    waitprocs()


def load_movie(movie_file):
    movie = retro.Movie(movie_file)
    duration = -1
    while movie.step():
        duration += 1
    movie = retro.Movie(movie_file)
    movie.step()
    emulator = retro.make(
        game=movie.get_game(),
        state=retro.State.NONE,
        use_restricted_actions=retro.Actions.ALL,
        players=movie.players)
    data = movie.get_state()
    emulator.initial_state = data
    emulator.reset()
    return emulator, movie, duration


def _play(movie, args, monitor_csv):
    video_file = None
    info_file = None
    npy_file = None
    if args.lossless in (u'png', u'ffv1'):
        ext = u'.mkv'
    else:
        ext = u'.mp4'

    basename = os.path.splitext(movie)[0]
    if not args.no_video:
        video_file = basename + ext
    if args.info_dict:
        info_file = basename + u'.json'
    if args.npy_actions:
        npy_file = basename + u'.npz'
    while True:
        emulator = None
        try:
            emulator, m, duration = load_movie(movie)
            if args.ending is not None:
                if args.ending < 0:
                    delay = duration + args.ending
                else:
                    delay = -(duration + args.ending)
            else:
                delay = 0
            playback_movie(emulator, m, monitor_csv, video_file, info_file,
                           npy_file, args.viewer, delay, args.lossless,
                           not args.no_audio)
            break
        except ConnectionRefusedError:
            pass
        except RuntimeError:
            if not os.path.exists(movie):
                raise FileNotFoundError(movie)
            raise
        finally:
            del emulator


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(u'movies', type=unicode, nargs=u'+')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(u'--jobs', u'-j', type=int, default=1)
    group.add_argument(u'--csv-out', u'-c', type=unicode)
    parser.add_argument(u'--ending', u'-e', type=int)
    parser.add_argument(u'--viewer', u'-v', type=unicode)
    parser.add_argument(u'--no-audio', u'-A', action=u'store_true')
    parser.add_argument(u'--no-video', u'-V', action=u'store_true')
    parser.add_argument(u'--info-dict', u'-i', action=u'store_true')
    parser.add_argument(u'--npy-actions', u'-a', action=u'store_true')
    parser.add_argument(
        u'--lossless', u'-L', type=unicode, choices=[u'mp4', u'mp4rgb', u'png', u'ffv1'])
    args = parser.parse_args(argv)
    monitor_csv = None
    monitor_file = None

    retro.data.add_integrations(retro.data.Integrations.ALL)

    if args.csv_out:
        m0 = retro.Movie(args.movies[0])
        game = m0.get_game()
        reward_fields = [u'r'] if m0.players == 1 else [
            u'r%d' % i for i in xrange(m0.players)
        ]
        monitor_file = open(args.csv_out, u'w')
        monitor_file.write(
            u'#{"t_start": 0.0, "gym_version": "gym_retro", "env_id": "%s"}\n' %
            game)
        monitor_csv = csv.DictWriter(
            monitor_file, fieldnames=reward_fields + [u'l', u't'])
        monitor_csv.writeheader()

    with Executor(args.jobs or None) as pool:
        list(
            pool.map(
                _play,
                *izip(*[(movie, args, monitor_csv) for movie in args.movies])))
    if monitor_file:
        monitor_file.close()


if __name__ == u'__main__':
    main()
