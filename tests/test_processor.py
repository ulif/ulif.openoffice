# -*- coding: utf-8 -*-
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
import pytest
import shutil
import tempfile
import zipfile
from ulif.openoffice.cachemanager import (
    CacheManager, CACHE_PER_USER)
from ulif.openoffice.helpers import remove_file_dir
from ulif.openoffice.processor import (
    BaseProcessor, MetaProcessor, OOConvProcessor, UnzipProcessor,
    ZipProcessor, Tidy, CSSCleaner, HTMLCleaner, Error)
from ulif.openoffice.testing import TestOOServerSetup

try:
    import unittest2 as unittest
except ImportError:
    import unittest

def get_unoconv_version():
    workdir = tempfile.mkdtemp()
    output = os.path.join(workdir, 'output')
    os.system('unoconv --version > %s' % output)
    output = open(output, 'r').readlines()
    version = output[0].split()[-1].split('.')
    shutil.rmtree(workdir)
    return tuple(version)
UNOCONV_VERSION = get_unoconv_version()

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

    def create_input(self):
        os.mkdir(os.path.join(self.workdir, 'input'))
        open(self.input, 'w').write('Hi there!')

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        os.mkdir(os.path.join(self.workdir, 'input'))
        os.mkdir(os.path.join(self.workdir, 'output'))
        self.input = os.path.join(self.workdir, 'input', 'sample.txt')
        self.output = os.path.join(self.workdir, 'output', 'result.txt')
        open(self.input, 'w').write('Hi there!')
        open(self.output, 'w').write('I am a (fake) converted doc')

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
        self.resultpath, metadata = proc.process(self.input)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
        assert self.resultpath.endswith('sample.html.zip')

    def test_process_xhtml_unzipped(self):
        proc = MetaProcessor(options={'oocp.out_fmt':'xhtml',
                                      'meta.procord':'unzip,oocp'})
        self.resultpath, metadata = proc.process(self.input)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
        assert self.resultpath.endswith('sample.xhtml')

    def test_process_html_unzipped(self):
        proc = MetaProcessor(options={'oocp.out_fmt':'html',
                                      'meta.procord':'unzip,oocp'})
        self.resultpath, metadata = proc.process(self.input)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
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

    def test_process_umlauts(self):
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        open(sample_file, 'wb').write('A sample with umlauts: ä')
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

    @pytest.mark.skipif("UNOCONV_VERSION < ('0', '5')")
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
        content = open(self.result_path, 'r').read()
        # these are PDF/A-1a specification requirements...
        assert '<pdfaid:part>1</pdfaid:part>' in content
        assert '<pdfaid:conformance>A</pdfaid:conformance>' in content

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
        assert sorted(namelist) == ['sample1.txt', 'sample2.txt']

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
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in contents

    def test_encoding_utf8(self):
        # make sure we get UTF-8 output and no special stuff.
        proc = Tidy()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        assert 'Ü' in contents
        assert '&Uuml;' not in contents

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
            '<link href="sample.css" rel="stylesheet" type="text/css"/>')
        assert 'sample.css' in os.listdir(resultdir)
        assert snippet in contents
        assert 'With umlaut: ä' in contents

    def test_cleaner_css_correct_css(self):
        # make sure we get a new CSS file and a link to it in HTML
        proc = CSSCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'font-family: ;' not in result_css

    def test_cleaner_css_minified(self):
        # make sure we can get minified CSS if we wish so.
        proc = CSSCleaner(options={'css_cleaner.minified' : '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p{margin-bottom:.21cm}span.c2' in result_css

    def test_cleaner_css_non_minified(self):
        # make sure we can get non-minified CSS if we wish so.
        proc = CSSCleaner(options={'css_cleaner.minified' : '0'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p {\n    margin-bottom: 0.21cm\n    }\n' in result_css

    def test_cleaner_css_default_minified(self):
        # make sure we can get non-minified CSS if we wish so.
        proc = CSSCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p{margin-bottom:.21cm}' in result_css

class TestHTMLCleanerProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.workdir2 = tempfile.mkdtemp()
        self.resultpath = None
        self.sample_path = os.path.join(self.workdir, 'sample.html')
        self.img_sample_path = os.path.join(self.workdir2, 'sample.html')
        self.img_file_path = os.path.join(self.workdir2,
                                     'image_sample_html_m20918026.gif')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample3.html'),
            self.sample_path)
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input',
                         'image_sample.html'),
            self.img_sample_path)
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input',
                         'image_sample_html_m20918026.gif'),
            self.img_file_path
            )
        return

    def tearDown(self):
        remove_file_dir(self.workdir)
        remove_file_dir(self.workdir2)
        remove_file_dir(self.resultpath)

    def test_cleaner(self):
        # make sure erranous headings are fixed by default.
        proc = HTMLCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        snippet1 = "%s" % (
            '<span class="u-o-headnum">1</span>Häding1')
        snippet2 = "%s" % (
            '<span class="u-o-headnum">1.1</span>Heading1.1')
        snippet3 = "%s" % (
            '<span class="u-o-headnum">1.2.</span>Heading1.2.')
        assert snippet1 in contents
        assert snippet2 in contents
        assert snippet3 in contents

    def test_option_fix_head_nums_true(self):
        # Make sure we respect the `fix_head_nums` option if true
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_head_nums': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        snippet1 = "%s" % (
            '<span class="u-o-headnum">1</span>Häding1')
        assert snippet1 in contents

    def test_option_fix_head_nums_false(self):
        # Make sure we respect the `fix_head_nums` option if false.
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_head_nums': 'False'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()

        resultdir = os.path.dirname(self.resultpath)
        snippet1 = "%s" % (
            '<h1 class="foo"><span class="u-o-headnum">1</span>Häding1</h1>')
        assert snippet1 not in contents

    def test_option_fix_img_links_false(self):
        # Make sure we respect the `fix_head_nums` option if true
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_img_links': '0'})
        self.resultpath, metadata = proc.process(
            self.img_sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        resultdir = os.path.dirname(self.resultpath)
        snippet = '<IMG SRC="image_sample_html_m20918026.gif"'
        list_dir = os.listdir(resultdir)
        assert snippet in contents
        assert 'image_sample_html_m20918026.gif' in list_dir
        assert 'sample_1.gif' not in list_dir

    def test_option_fix_img_links_true(self):
        # Make sure we respect the `fix_img_links` option if true
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_img_links': '1'})
        self.resultpath, metadata = proc.process(
            self.img_sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        resultdir = os.path.dirname(self.resultpath)
        snippet = '<IMG SRC="image_sample_html_m20918026.gif"'
        list_dir = os.listdir(resultdir)
        assert snippet not in contents
        assert 'image_sample_html_m20918026.gif' not in list_dir
        assert 'sample_1.gif' in list_dir

    def test_option_fix_sdfields_false(self):
        # Make sure we respect the `fix_sdtags` option if false
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_sdfields': '0'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        snippet = '<sdfield type="PAGE">'
        assert snippet in contents

    def test_option_fix_sdfields_true(self):
        # Make sure we respect the `fix_sdtags` option if false
        proc = HTMLCleaner(
            options = {
                'html_cleaner.fix_sdfields': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error':False})
        contents = open(self.resultpath, 'rb').read()
        snippet = '<sdfield type="PAGE">'
        assert snippet not in contents

    def test_option_invalid(self):
        # Make sure we complain when trash is set as `fix_head_nums`.
        self.assertRaises(
            ValueError,
            HTMLCleaner, options={'html_cleaner.fix_head_nums': 'foo'})
        self.assertRaises(
            ValueError,
            HTMLCleaner, options={'html_cleaner.fix_img_links': 'foo'})
        self.assertRaises(
            ValueError,
            HTMLCleaner, options={'html_cleaner.fix_sdfields': 'foo'})


    def test_rename_img_files(self):
        proc = HTMLCleaner(
            options = {'html_cleaner.fix_img_links': '1'})
        proc.rename_img_files(
            self.workdir2,
            {'image_sample_html_m20918026.gif': 'sample_1.gif'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'sample_1.gif' in list_dir
        assert 'image_sample_html_m20918026.gif' not in list_dir

    def test_rename_img_files_no_src(self):
        # We cope with not existing source files
        proc = HTMLCleaner(
            options = {'html_cleaner.fix_img_links': '1'})
        proc.rename_img_files(
            self.workdir2,
            {'not-existing-filename': 'sample_1.gif'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'sample_1.gif' not in list_dir

    def test_rename_img_files_dst_exists_already(self):
        # We cope with dest files that already exist
        proc = HTMLCleaner(
            options = {'html_cleaner.fix_img_links': '1'})
        proc.rename_img_files(
            self.workdir2,
            {'image_sample_html_m20918026.gif':
                 'image_sample_html_m20918026.gif'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'image_sample_html_m20918026.gif' in list_dir

    def test_rename_img_files_src_is_dir(self):
        # We cope with src files that are in fact dirs
        proc = HTMLCleaner(
            options = {'html_cleaner.fix_img_links': '1'})
        os.mkdir(os.path.join(self.workdir2, 'some_dir'))
        proc.rename_img_files(
            self.workdir2,
            {'some_dir': 'sample.jpg'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'sample.jpg' not in list_dir

class TestErrorProcessor(unittest.TestCase):

    def test_error(self):
        proc = Error()
        path, metadata = proc.process(None, {})
        assert path is None
        assert 'error-descr' in metadata.keys()
