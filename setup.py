#!/usr/bin/python -tt
# -*- coding: UTF-8 -*-
# vim: sw=4 ts=4 expandtab ai
#
# $Id: setup.py 82 2007-11-11 23:01:26Z kad $

from distutils.core import setup

setup (name = "sbdmock",
    description = "Scratchbox debian package builder",
    version = open("debian/changelog").readline().split(' ')[1][1:-1],
    author = "Alexandr D. Kanevskiy",
    author_email = "packages@bifh.org",
    url = "http://bifh.org/wiki/sbdmock",
    license = "GPL",
    scripts = ['scripts/sbdmock', 'scripts/sbdarchtarget' ],
    requires = ['minideblib', ],
    long_description = "Scratchbox debian package builder",
    keywords = "python debian dpkg scratchbox",
    platforms="Python 2.3 and later.",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: Unix",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: System :: Archiving :: Packaging",
        ]
    )

