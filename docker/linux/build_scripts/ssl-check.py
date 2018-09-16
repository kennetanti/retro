# cf. https://github.com/pypa/manylinux/issues/53

from __future__ import absolute_import
GOOD_SSL = u"https://google.com"
BAD_SSL = u"https://self-signed.badssl.com"

import sys

print u"Testing SSL certificate checking for Python:", sys.version

if (sys.version_info[:2] < (3, 4)):
    print u"This version never checks SSL certs; skipping tests"
    sys.exit(0)

if sys.version_info[0] >= 3:
    from urllib2 import urlopen
    EXC = OSError
else:
    from urllib import urlopen
    EXC = IOError

print u"Connecting to %s should work" % (GOOD_SSL, )
urlopen(GOOD_SSL)
print u"...it did, yay."

print u"Connecting to %s should fail" % (BAD_SSL, )
try:
    urlopen(BAD_SSL)
    # If we get here then we failed:
    print u"...it DIDN'T!!!!!11!!1one!"
    sys.exit(1)
except EXC:
    print u"...it did, yay."
