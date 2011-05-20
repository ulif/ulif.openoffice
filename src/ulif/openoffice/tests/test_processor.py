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
import zipfile
from ulif.openoffice.helpers import remove_file_dir
from ulif.openoffice.processor import (
    BaseProcessor, MetaProcessor, OOConvProcessor, UnzipProcessor,
    ZipProcessor, Tidy, CSSCleaner, Error)
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

    def test_get_own_options_defaults(self):
        proc = SemiBaseProcessor()
        proc.defaults = {'key1': 'notset'}
        result = proc.get_own_options({})
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

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None

    def tearDown(self):
        remove_file_dir(self.workdir)
        remove_file_dir(self.resultpath)

    def test_no_options(self):
        # We cope with no options set
        proc = MetaProcessor()
        assert len(proc.options) == 1
        assert 'procord' in proc.options.keys()
        return

    def test_ignored_options(self):
        # We ignore keys not in default dict
        proc = MetaProcessor(options={'meta.foo':12})
        assert len(proc.options) == 1
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
        assert result == 'procord=oocp,oocp'

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

    def test_process_default(self):
        proc = MetaProcessor(options={})
        input_path = os.path.join(self.workdir, 'sample.txt')
        open(input_path, 'wb').write('Hi there!')
        self.resultpath, metadata = proc.process(input_path)
        assert metadata == {'error': False, 'oocp_status':0}
        assert self.resultpath.endswith('sample.html.zip')

    def test_process_xhtml_unzipped(self):
        proc = MetaProcessor(options={'oocp.out_fmt':'xhtml',
                                      'meta.procord':'unzip,oocp'})
        input_path = os.path.join(self.workdir, 'sample.txt')
        open(input_path, 'wb').write('Hi there!')
        self.resultpath, metadata = proc.process(input_path)
        assert metadata == {'error': False, 'oocp_status':0}
        assert self.resultpath.endswith('sample.xhtml')
        #print open(self.resultpath, 'r').read()

    def test_process_html_unzipped(self):
        proc = MetaProcessor(options={'oocp.out_fmt':'html',
                                      'meta.procord':'unzip,oocp'})
        input_path = os.path.join(self.workdir, 'sample.txt')
        open(input_path, 'wb').write('Hi there!')
        self.resultpath, metadata = proc.process(input_path)
        assert metadata == {'error': False, 'oocp_status':0}
        assert self.resultpath.endswith('sample.html')


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

    def test_process_src_not_in_result(self):
        # Make sure the input file does not remain in result dir
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        dir_list = os.listdir(os.path.dirname(self.result_path))
        assert 'sample.txt' not in dir_list

    def test_process_pdf_simple(self):
        proc = OOConvProcessor(
            options = {
                'oocp.out_fmt': 'pdf',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert self.result_path.endswith('sample.pdf')

    def test_process_pdf_as_pda(self):
        # make sure we can produce PDF/A output
        proc = OOConvProcessor(
            options = {
                'oocp.out_fmt': 'pdf',
                'oocp.pdf_version': '1',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert 'xmlns:pdf="http://ns.adobe.com/pdf/1.3/"' in open(
            self.result_path, 'rb').read()

    def test_process_pdf_as_non_pda(self):
        # make sure we can produce non-PDF/A output
        proc = OOConvProcessor(
            options = {
                'oocp.out_fmt': 'pdf',
                'oocp.pdf_version': '0',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert 'xmlns:pdf="http://ns.adobe.com/pdf/1.3/"' not in open(
            self.result_path, 'rb').read()

class TestUnzipProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.zipfile_path = os.path.join(self.workdir, 'sample2.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample2.zip'),
            self.zipfile_path)
        self.zipfile2_path = os.path.join(self.workdir, 'sample1.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            self.zipfile2_path)
        self.result_path = None
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        if self.result_path is None:
            return
        if not os.path.exists(self.result_path):
            return
        if os.path.isfile(self.result_path):
            self.result_path = os.path.dirname(self.result_path)
        shutil.rmtree(self.result_path)
        return

    def test_simple(self):
        proc = UnzipProcessor()
        self.result_path, metadata = proc.process(self.zipfile_path, {})
        assert self.result_path.endswith('simple.txt')

    def test_one_file_only(self):
        # if a zip file contains more than one file, that's an error
        proc = UnzipProcessor()
        self.result_path, metadata = proc.process(self.zipfile2_path,
                                                  {'error':False})
        assert metadata['error'] is True
        assert self.result_path is None

class TestZipProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.result_path = None
        return

    def tearDown(self):
        if os.path.isdir(self.workdir):
            shutil.rmtree(self.workdir)
        if self.result_path is None:
            return
        if not os.path.exists(self.result_path):
            return
        if os.path.isfile(self.result_path):
            self.result_path = os.path.dirname(self.result_path)
        shutil.rmtree(self.result_path)
        return

    def test_simple(self):
        sample_path = os.path.join(self.workdir, 'sample1.txt')
        open(sample_path, 'wb').write('Hi there!')
        open(
            os.path.join(self.workdir, 'sample2.txt'),
            'wb').write('Hello again')
        proc = ZipProcessor()
        self.result_path, metadata = proc.process(sample_path,
                                                  {'error':False})
        assert zipfile.is_zipfile(self.result_path)
        zip_file = zipfile.ZipFile(self.result_path, 'r')
        namelist = zip_file.namelist()
        assert namelist == ['sample1.txt', 'sample2.txt']

class TestTidyProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        self.sample_path = os.path.join(self.workdir, 'sample.html')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.html'),
            self.sample_path)
        return

    def tearDown(self):
        remove_file_dir(self.workdir)
        remove_file_dir(self.resultpath)

    def test_default_xhtml(self):
        # make sure by default we get XHTML output from HTML.
        proc = Tidy()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        assert '"-//W3C//DTD XHTML 1.0 Transitional//EN"' in contents
        #from ulif.openoffice.helpers import copy_to_secure_location
        #new = copy_to_secure_location(self.resultpath)
        #print "NEW: ", new

class TestCSSCleanerProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        self.sample_path = os.path.join(self.workdir, 'sample.html')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample2.html'),
            self.sample_path)
        return

    def tearDown(self):
        remove_file_dir(self.workdir)
        remove_file_dir(self.resultpath)

    def test_cleaner(self):
        # make sure we get a new CSS file and a link to it in HTML
        proc = CSSCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        snippet = "%s" % (
            '<link rel="stylesheet" type="text/css" href="sample.css" />')
        assert 'sample.css' in os.listdir(resultdir)
        assert snippet in open(self.resultpath, 'rb').read()

class TestErrorProcessor(unittest.TestCase):

    def test_error(self):
        proc = Error()
        path, metadata = proc.process(None, {})
        assert path is None
        assert 'error-descr' in metadata.keys()
