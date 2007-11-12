#!/usr/bin/python -tt
# vim: sw=4 ts=4 expandtab ai 
#
# This file is part of sbdmock
#
# Copyright (C) 2005-2007 Alexandr D. Kanevskiy
#
# Contact: Alexandr D. Kanevskiy <packages@bifh.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# $Id$

import sys
import types
import re
from exceptions import Exception
from optparse import OptionParser

from minideblib.ChangeFile import ChangeFile
from pprint import pformat

__revision__ = "r"+"$Revision$"[11:-2]

debugging = False
# supported_arches sorted by the preference to use for 'all' source architecture 
supported_arches = ['i386', 'armel', 'arm', 'ui386', 'uarm']
debian_arches = [ 'alpha', 'amd64', 'arm', 'armeb', 'armel', 'hppa', 'i386', 'ia64', 'm32r', 'm68k', 'mips', 'mipsel', 'powerpc', 'ppc64', 's390', 's390x', 'sh3', 'sh3eb', 'sh4', 'sh4eb', 'sparc' ]

def error(msg):
    print >> sys.stderr, msg

def debug(msg):
    global debugging
    if debugging:
        print "DEBUG: %s" %  msg


def command_parse():
    """return options and args from parsing the command line"""

    usage = """
    usage: sbdarchtarget [options] /path/to/dsc
    """
    parser = OptionParser(usage=usage, version=__VERSION__)
    parser.add_option("--arch", "-a",  action ="append", type="string", dest="arch", 
             default=None, help="arch:target mapping")
    parser.add_option("--debug", "-d", action ="store_true", dest="debug",
             default=False, help="Output copious debugging information")
    return parser.parse_args()

def main():
    global debugging
    # cli option parsing
    (options, args) = command_parse()

    if not options.arch:
        error("No arch<->target mappings defined")
        sys.exit(10)

    if len(args) != 1:
        error("You should specify only one path to debian sorce package (dsc)")
        sys.exit(20)

    if options.debug:
        debugging = True

    #debug(pformat(options))

    arches = {}
    arches['any'] = []

    if options.arch:
        for line in options.arch:
            if line.find(":") < 0:
                error("Invalid arch mapping specified: %s" % line)
            else:
                (arch, target) = line.split(":")
                if arch not in supported_arches:
                    error("Unsupported arch specified: %s" % arch)
                else:
                    if arch not in arches:
                        arches[arch] = []
                    arches[arch].append(target)
                    if arch in debian_arches:
                        arches['any'].append(target)

    # special case for packages which produce only arch independed binaries.
    arches['all'] = []
    for arch in supported_arches:
        if arch in arches:
            arches['all'].append(arches[arch][0])
            break
    # nothing found, pick first from 'any'
    if not arches['all'] and arches['any']:
        arches['all'].append(arches['any'][0])

    debug(pformat(arches))

    cdsc = ChangeFile()
    try:
        cdsc.load_from_file(args[0])
    except Exception, ex:
        error("Parsing failed: %s" % ex)
        sys.exit(20)

    debug(pformat(cdsc))

    result = []
    if cdsc.has_key('scratchbox-architecture'):
        # Special case. Ignore main Architecture tag
        for targ in re.split(",? +", cdsc['scratchbox-architecture']):
            if arches.has_key(targ.strip()):
                result.append(arches[targ.strip()])
            else:
                error("Warning: Unknown scratchbox arch: '%s'" % targ.strip())
    else:
        for targ in re.split(",? +", cdsc['architecture']):
            if arches.has_key(targ.strip()):
                result.append(arches[targ.strip()])
            else:
                error("Warning: Unknown arch: '%s'" % targ.strip())
   
    debug(pformat(result))
    if len(result) == 0:
        error("Error: Can't find any suitable target for %s" % args[0])
        sys.exit(30)
    else:
        for targ in result:
            if type(targ) is types.ListType:
                for line in targ:
                    print line
            elif type(targ) is types.StringType:
                print targ
            else:
                # wtf?
                pass

if __name__ == '__main__':
    main()
