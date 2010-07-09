##
## tests.py
## Login : <uli@pu.smp.net>
## Started on  Wed Aug 26 02:18:41 2009 Uli Fouquet
## $Id$
## 
## Copyright (C) 2009 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
"""Test `ulif.openoffice`.
"""
import doctest
import os
import pkg_resources
import re
import unittest
import zc.buildout.testing
from zope.testing import renormalizing

VERSION = pkg_resources.get_distribution('ulif.openoffice').version

checker = renormalizing.RENormalizing([
    zc.buildout.testing.normalize_path,
    (re.compile(
        "Couldn't find index page for '[a-zA-Z0-9.]+' "
        "\(maybe misspelled\?\)"
        "\n"),
     ''),
    (re.compile("""['"][^\n"']+z3c.recipe.i18n[^\n"']*['"],"""),
     "'/z3c.recipe.i18n',"),
    (re.compile('#![^\n]+\n'), ''),
    (re.compile('-\S+-py\d[.]\d(-\S+)?.egg'),
     '-pyN.N.egg',),
    (re.compile(VERSION), '<VERSION>',),
    ])


def setUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    zc.buildout.testing.install_develop('ulif.openoffice', test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)
    # Create a home that openoffice.org can fiddle around with...
    os.mkdir('home')
    os.environ['HOME'] = os.path.abspath(os.path.join(os.getcwd(), 'home'))

def test_suite():
    testfiles = [
        'cachemanager.txt',
        'README.txt',
        'pyunoctl.txt',
        'restserver.txt'
        ]
    suite = unittest.TestSuite()
    for testfile in testfiles:
        abspath = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)
                ),
            testfile
            )

        suite.addTest(
            doctest.DocFileSuite(
                abspath,
                module_relative = False,
                setUp = setUp,
                tearDown = zc.buildout.testing.buildoutTearDown,
                optionflags = doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE,
                checker = checker,
                ))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTests='test_suite')
