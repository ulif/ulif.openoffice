##
## test_processor.py
## Login : <uli@pu.smp.net>
## Started on  Sat Apr 30 04:46:38 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
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
"""
Test processors defined in this package.
"""
from ulif.openoffice.processor import MetaProcessor, OOConvProcessor
from ulif.openoffice.testing import TestOOServerSetup

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestMetaProcessor(unittest.TestCase):

    def test_no_options(self):
        # We cope with no options set
        proc = MetaProcessor()
        assert len(proc.options) == 3
        assert 'prepord' in proc.options.keys()
        return

    def test_ignored_options(self):
        # We ignore keys not in default dict
        proc = MetaProcessor(options={'meta.foo':12})
        assert len(proc.options) == 3
        assert 'foo' not in proc.options.keys()

    def test_non_meta_options(self):
        # We ignore options not determined for the meta processor
        proc = MetaProcessor(options={'foo.bar':12})
        assert 'bar' not in proc.options.keys()

    def test_option_set(self):
        # We respect options set if available in the defaults dict
        proc = MetaProcessor(options={'meta.procord':'oocp,oocp'})
        assert proc.options['procord'] == 'oocp,oocp'

    def test_options_as_strings(self):
        proc = MetaProcessor(options={'meta.procord':'oocp, oocp'})
        result = proc.get_options_as_string()
        assert result == 'postpord=prepord=procord=oocp,oocp'

    def test_options_invalid(self):
        # Make sure that invalid options lead to exceptions
        self.assertRaises(
            ValueError,
            MetaProcessor, options={'meta.procord':'oop,nonsense'})
        return

    def test_avail_processors(self):
        # Make sure processors defined via entry points are found
        proc = MetaProcessor(options={'meta.procord':'oocp, oocp'})
        assert proc.avail_procs['oocp'] is OOConvProcessor
        assert len(proc.avail_procs.items()) > 0

class TestOOConvProcessor(TestOOServerSetup):
    def test_no_options(self):
        # We cope with no options set
        proc = OOConvProcessor()
        assert proc.options['out_fmt'] == 'html'
        return

    def test_option_out_fmt_invalid(self):
        self.assertRaises(
            ValueError,
            OOConvProcessor, options={'oocp.out_fmt':'odt'})
        return
