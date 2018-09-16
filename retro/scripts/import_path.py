#!/usr/bin/env python
from __future__ import absolute_import
import retro.data
import os
import sys


def main():
    potential_roms = []
    for path in sys.argv[1:]:
        for base, _, files in os.walk(sys.argv[1]):
            potential_roms.extend(os.path.join(base, file) for file in files)

    print u'Importing %i potential games...' % len(potential_roms)
    retro.data.merge(*potential_roms, quiet=False)


if __name__ == u'__main__':
    main()
