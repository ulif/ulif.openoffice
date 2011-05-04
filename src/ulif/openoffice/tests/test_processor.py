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
import os
import shutil
import tempfile
from ulif.openoffice.processor import (
    BaseProcessor, MetaProcessor, OOConvProcessor)
from ulif.openoffice.testing import TestOOServerSetup

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class SemiBaseProcessor(BaseProcessor):
    # A BaseProcessor that does not raise NotImplemented on creation
    def validate_options(self):
        pass
    
class TestBaseProcessor(unittest.TestCase):

    def notest_get_own_options_defaults(self):
        proc = SemiBaseProcessor()
        proc.defaults = {'key1': 'notset'}
        result = proc.get_own_options()
        assert result == {'key1': 'notset'}
        
    def test_get_own_options(self):
        proc = SemiBaseProcessor()
        proc.defaults = {'key1': 'notset'}
        result = proc.get_own_options({'base.key1':'set'})
        assert result == {'key1': 'set'}

    def test_get_own_options_ignore_other(self):
        # ignore options that have not the correct prefix
        proc = SemiBaseProcessor()
        proc.defaults = {'key1': 'notset'}
        result = proc.get_own_options({'key1':'set'})
        assert result == {'key1': 'notset'}

    def test_option_ne_defaults(self):
        # make sure after creation options are not the same object as defaults
        proc = SemiBaseProcessor()
        assert proc.options is not proc.defaults
        
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

    def test_build_pipeline_single(self):
        proc = MetaProcessor(options={'meta.procord':'oocp'})
        result = proc._build_pipeline()
        assert result == (OOConvProcessor,)

    def test_build_pipeline_twoitems(self):
        proc = MetaProcessor(options={'meta.procord':'oocp, oocp'})
        result = proc._build_pipeline()
        assert result == (OOConvProcessor, OOConvProcessor)

    def test_build_pipeline_empty(self):
        proc = MetaProcessor(options={'meta.procord':''})
        result = proc._build_pipeline()
        assert result is ()
        
class TestOOConvProcessor(TestOOServerSetup):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.result_path = None
        return

    def tearDown(self):
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        if self.result_path is None:
            return
        if not os.path.exists(self.result_path):
            return
        if os.path.isfile(self.result_path):
            self.result_path = os.path.dirname(self.result_path)
        shutil.rmtree(self.result_path)
        return

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

    def test_process_simple(self):
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert self.result_path.endswith('sample.html')

