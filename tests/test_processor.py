# -*- coding: utf-8 -*-
##
## test_processor.py
##
## Copyright (C) 2011, 2013, 2015 Uli Fouquet
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
from argparse import ArgumentParser
from ulif.openoffice.helpers import remove_file_dir
from ulif.openoffice.options import ArgumentParserError, Options
from ulif.openoffice.processor import (
    BaseProcessor, MetaProcessor, OOConvProcessor, UnzipProcessor,
    ZipProcessor, Tidy, CSSCleaner, HTMLCleaner, Error, processor_order)
from ulif.openoffice.testing import TestOOServerSetup, ConvertLogCatcher
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


class TestProcessorHelpers(unittest.TestCase):

    def test_processor_order_valid(self):
        assert processor_order('unzip, zip') == ('unzip', 'zip')
        assert processor_order('zip, unzip') == ('zip', 'unzip')
        assert processor_order('zip') == ('zip', )
        assert processor_order(',,,') == ()
        assert processor_order('') == ()

    def test_processor_order_invalid(self):
        # we do accept only valid processor names
        self.assertRaises(
            ValueError, processor_order, 'unzip, invalid, zip')


class TestBaseProcessor(unittest.TestCase):

    def test_process_raises_not_implemented(self):
        # make sure a call to process raises something
        proc = BaseProcessor()
        self.assertRaises(
            NotImplementedError, proc.process, None, None)

    def test_args(self):
        # each processor should provide an arparser compatible list of
        # acceptable args that can be fed to argparsers.
        proc = BaseProcessor()
        assert proc.args == []


class TestMetaProcessor(unittest.TestCase):

    def create_input(self):
        os.mkdir(os.path.join(self.workdir, 'input'))
        with open(self.input, 'w') as fd:
            fd.write('Hi there!')

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        os.mkdir(os.path.join(self.workdir, 'input'))
        os.mkdir(os.path.join(self.workdir, 'output'))
        self.input = os.path.join(self.workdir, 'input', 'sample.txt')
        self.output = os.path.join(self.workdir, 'output', 'result.txt')
        with open(self.input, 'w') as fd:
            fd.write('Hi there!')
        with open(self.output, 'w') as fd:
            fd.write('I am a (fake) converted doc')

    def tearDown(self):
        remove_file_dir(self.workdir)
        remove_file_dir(self.resultpath)

    def test_no_options(self):
        # We cope with no options set
        proc = MetaProcessor()
        #assert len(proc.options) == 1
        assert 'meta_processor_order' in proc.options.keys()
        return

    def test_ignored_options(self):
        # We ignore keys not in default dict
        proc = MetaProcessor(options={'meta-foo': '12'})
        assert 'meta-foo' not in proc.options.keys()

    def test_non_meta_options(self):
        # We ignore options not determined for the meta processor
        proc = MetaProcessor(options={'foo.bar': '12'})
        assert 'bar' not in proc.options.keys()

    def test_option_set(self):
        # We respect options set if available in the defaults dict
        proc = MetaProcessor(options={'meta-procord': 'oocp,oocp'})
        assert proc.options['meta_processor_order'] == ('oocp', 'oocp')

    def test_options_as_strings(self):
        proc = MetaProcessor(options={'meta.procord': 'oocp, oocp'})
        result = proc.get_options_as_string()
        assert result == (
            "css_cleaner_minified=True"
            "css_cleaner_prettify_html=False"
            "html_cleaner_fix_heading_numbers=True"
            "html_cleaner_fix_image_links=True"
            "html_cleaner_fix_sd_fields=True"
            "meta_processor_order=('unzip', 'oocp', 'tidy', 'html_cleaner', "
            "'css_cleaner', 'zip')"
            "oocp_hostname=localhost"
            "oocp_output_format=html"
            "oocp_pdf_tagged=False"
            "oocp_pdf_version=False"
            "oocp_port=2002"
        )

    def test_options_invalid(self):
        # Make sure that invalid options lead to exceptions
        self.assertRaises(
            ArgumentParserError,
            MetaProcessor, options={'meta-procord': 'oop,nonsense'})
        return

    def test_avail_processors(self):
        # Make sure processors defined via entry points are found
        proc = MetaProcessor(options={'meta-procord': 'oocp, oocp'})
        assert proc.avail_procs['oocp'] is OOConvProcessor
        assert len(proc.avail_procs.items()) > 0

    def test_build_pipeline_single(self):
        proc = MetaProcessor(options={'meta-procord': 'oocp'})
        result = proc._build_pipeline()
        assert result == (OOConvProcessor,)

    def test_build_pipeline_twoitems(self):
        proc = MetaProcessor(options={'meta-procord': 'oocp, oocp'})
        result = proc._build_pipeline()
        assert result == (OOConvProcessor, OOConvProcessor)

    def test_build_pipeline_empty(self):
        proc = MetaProcessor(options={'meta-procord': ''})
        result = proc._build_pipeline()
        assert result == ()

    def test_build_pipeline_empty_elements(self):
        proc = MetaProcessor(options={'meta-procord': 'oocp,,,oocp'})
        result = proc._build_pipeline()
        assert result == (OOConvProcessor, OOConvProcessor)

    def test_process_default(self):
        proc = MetaProcessor(options={})
        self.resultpath, metadata = proc.process(self.input)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
        assert self.resultpath.endswith('sample.html.zip')

    def test_process_xhtml_unzipped(self):
        proc = MetaProcessor(options={'oocp-out-fmt': 'xhtml',
                                      'meta-procord': 'unzip,oocp'})
        self.resultpath, metadata = proc.process(self.input)
        assert os.path.isfile(self.resultpath)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
        assert open(self.resultpath, 'r').read().startswith('<?xml ')
        assert self.resultpath.endswith('sample.html')

    def test_process_html_unzipped(self):
        proc = MetaProcessor(options={'oocp-out-fmt': 'html',
                                      'meta-procord': 'unzip,oocp'})
        self.resultpath, metadata = proc.process(self.input)
        assert os.path.isfile(self.resultpath)
        assert metadata['error'] is False and metadata['oocp_status'] == 0
        assert open(self.resultpath, 'r').read().startswith('<!DOCTYPE')
        assert self.resultpath.endswith('sample.html')

    def test_process_with_errors(self):
        proc = MetaProcessor(options={'meta-procord': 'error'})
        self.resultpath, metadata = proc.process(self.input)
        assert self.resultpath is None
        assert metadata == {
            'error': True,
            'error-descr': 'Intentional error. Please ignore',
            }

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in MetaProcessor.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {
            'meta_processor_order':
            ('unzip', 'oocp', 'tidy', 'html_cleaner', 'css_cleaner', 'zip',)
            }
        # explicitly set value (different from default)
        result = vars(parser.parse_args(['-meta-procord', 'unzip,oocp,zip']))
        assert result == {
            'meta_processor_order': ('unzip', 'oocp', 'zip')}


class FakeUnoconvContext(object):
    # A context manager that modifies environment to find a given
    # unoconv replacement before other executables.
    #
    # Copies the given fake unoconv to a new dir, modifies PATH and
    # resets everything finally.
    #
    # If env has no PATH, nothing is changed.
    def __init__(self, unoconv_path, basename='unoconv'):
        self.unoconv_path = unoconv_path
        self.basename = basename

    def __enter__(self):
        self.env = os.environ.copy()
        self.old_env_path = self.env.get('PATH', None)
        if self.old_env_path is None:
            return None
        # Create a new dir to store a copy of the desired executable
        self.new_bindir = tempfile.mkdtemp()
        self.new_unoconv_path = os.path.join(
            self.new_bindir, self.basename)
        shutil.copy2(self.unoconv_path, self.new_unoconv_path)
        # Set env PATH to point to the new directory first
        os.environ['PATH'] = ':'.join([self.new_bindir, os.environ['PATH']])

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_env_path is None:
            return False
        os.environ['PATH'] = self.env['PATH']
        if os.path.isdir(self.new_bindir):
            shutil.rmtree(self.new_bindir)
        return False


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

    def failing_unoconv_context(self):
        # inject local ``fake_unoconv`` executable (which returns
        # error state unconditionally) into PATH.
        fake_unoconv_path = os.path.join(
            os.path.dirname(__file__), 'fake_unoconv')
        return FakeUnoconvContext(fake_unoconv_path)

    def test_no_options(self):
        # We cope with no options set
        proc = OOConvProcessor()
        assert proc.options['oocp_output_format'] == 'html'
        return

    def test_option_out_fmt_invalid(self):
        self.assertRaises(
            ArgumentParserError,
            OOConvProcessor, options={'oocp-out-fmt': 'odt'})
        return

    def test_process_simple(self):
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert self.result_path.endswith('sample.html')

    def test_process_umlauts(self):
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample with umlauts: ä')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert self.result_path.endswith('sample.html')

    def test_process_src_not_in_result(self):
        # Make sure the input file does not remain in result dir
        proc = OOConvProcessor()
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        dir_list = os.listdir(os.path.dirname(self.result_path))
        assert 'sample.txt' not in dir_list

    def test_process_pdf_simple(self):
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'pdf',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert self.result_path.endswith('sample.pdf')

    @pytest.mark.skipif("UNOCONV_VERSION < ('0', '6')")
    def test_process_pdf_as_pda(self):
        # make sure we can produce PDF/A output
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'pdf',
                'oocp-pdf-version': '1',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        content = open(self.result_path, 'r').read()
        # these are PDF/A-1a specification requirements...
        assert '<pdfaid:part>1</pdfaid:part>' in content
        assert '<pdfaid:conformance>A</pdfaid:conformance>' in content

    def test_process_pdf_as_non_pda(self):
        # make sure we can produce non-PDF/A output
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'pdf',
                'oocp-pdf-version': '0',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert 'xmlns:pdf="http://ns.adobe.com/pdf/1.3/"' not in open(
            self.result_path, 'rb').read()

    def test_process_pdf_tagged(self):
        # make sure we can produce non-PDF/A output
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'pdf',
                'oocp-pdf-tagged': '1',
                }
            )
        sample_file = os.path.join(self.workdir, 'sample.txt')
        with open(sample_file, 'wb') as fd:
            fd.write('A sample')
        self.result_path, meta = proc.process(sample_file, {})
        assert meta['oocp_status'] == 0
        assert 'xmlns:pdf="http://ns.adobe.com/pdf/1.3/"' not in open(
            self.result_path, 'rb').read()

    @pytest.mark.skipif("not os.environ.get('PATH', None)")
    def test_failing_op(self):
        proc = OOConvProcessor(Options())
        sample_file = os.path.join(self.workdir, b'sample.txt')
        with open(sample_file, 'w') as fd:
            fd.write(b'A sample')
        with self.failing_unoconv_context():
            # the fake unoconv will return error unconditionally
            self.result_path, meta = proc.process(sample_file, Options())
        assert meta[b'oocp_status'] == 1
        assert self.result_path is None
        return

    def test_pdf_props_wo_pdf_out(self):
        # PDF props are set only when pdf output format is required
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'html',
                }
            )
        sample_file = os.path.join(self.workdir, b'sample.txt')
        with open(sample_file, 'w') as fd:
            fd.write(b'A sample')
        log_catcher = ConvertLogCatcher()
        self.result_path, meta = proc.process(sample_file, {})
        output = log_catcher.get_log_messages()
        assert '-e SelectPdfVersion' not in output

    def test_pdf_props_with_pdf_out(self):
        # PDF props are set only when pdf output format is required
        proc = OOConvProcessor(
            options={
                'oocp-out-fmt': 'pdf',
                }
            )
        sample_file = os.path.join(self.workdir, b'sample.txt')
        with open(sample_file, 'w') as fd:
            fd.write(b'A sample')
        log_catcher = ConvertLogCatcher()
        self.result_path, meta = proc.process(sample_file, {})
        output = log_catcher.get_log_messages()
        assert '-e SelectPdfVersion' in output

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in OOConvProcessor.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {'oocp_output_format': 'html',
                          'oocp_pdf_version': False,
                          'oocp_pdf_tagged': False,
                          'oocp_hostname': 'localhost',
                          'oocp_port': 2002,
                          }
        # explicitly set value (different from default)
        result = vars(parser.parse_args(['-oocp-out-fmt', 'pdf',
                                         '-oocp-pdf-version', '1',
                                         '-oocp-pdf-tagged', '1',
                                         '-oocp-host', 'example.com',
                                         '-oocp-port', '1234', ]))
        assert result == {'oocp_output_format': 'pdf',
                          'oocp_pdf_version': True,
                          'oocp_pdf_tagged': True,
                          'oocp_hostname': 'example.com',
                          'oocp_port': 1234}


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
        self.result_path, metadata = proc.process(
            self.zipfile2_path, {'error': False})
        assert metadata['error'] is True
        assert self.result_path is None

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in UnzipProcessor.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {}
        # explicitly set value (different from default)
        result = vars(parser.parse_args([]))
        assert result == {}


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
        with open(sample_path, 'wb') as fd:
            fd.write('Hi there!')
        with open(
                os.path.join(self.workdir, 'sample2.txt'),
                'wb') as fd:
            fd.write('Hello again')
        proc = ZipProcessor()
        self.result_path, metadata = proc.process(
            sample_path, {'error': False})
        assert zipfile.is_zipfile(self.result_path)
        zip_file = zipfile.ZipFile(self.result_path, 'r')
        namelist = zip_file.namelist()
        assert sorted(namelist) == ['sample1.txt', 'sample2.txt']

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in ZipProcessor.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {}
        # explicitly set value (different from default)
        result = vars(parser.parse_args([]))
        assert result == {}


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
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in contents

    def test_encoding_utf8(self):
        # make sure we get UTF-8 output and no special stuff.
        proc = Tidy()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()
        assert 'Ü' in contents
        assert '&Uuml;' not in contents

    def test_non_html_ignored(self):
        # we do not try to tidy non html/xhtml files
        proc = Tidy()
        sample_path = os.path.join(self.workdir, 'sample.txt')
        with open(sample_path, 'w') as fd:
            fd.write('Sample file.')
        self.resultpath, metadata = proc.process(
            sample_path, {'error': False})
        # the document path hasn't changed
        assert self.resultpath == sample_path

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in Tidy.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {}
        # explicitly set value (different from default)
        result = vars(parser.parse_args([]))
        assert result == {}


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
            self.sample_path, {'error': False})
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
            self.sample_path, {'error': False})

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'font-family: ;' not in result_css

    def test_cleaner_css_minified(self):
        # make sure we can get minified CSS if we wish so.
        proc = CSSCleaner(options={'css_cleaner.minified': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p{margin-bottom:.21cm}span.c2' in result_css

    def test_cleaner_css_non_minified(self):
        # make sure we can get non-minified CSS if we wish so.
        proc = CSSCleaner(options={'css-cleaner-min': '0'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p {\n    margin-bottom: 0.21cm\n    }\n' in result_css

    def test_cleaner_css_default_minified(self):
        # make sure we can get non-minified CSS if we wish so.
        proc = CSSCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})

        resultdir = os.path.dirname(self.resultpath)
        result_css = open(
            os.path.join(resultdir, 'sample.css'), 'rb').read()
        assert 'p{margin-bottom:.21cm}' in result_css

    def test_cleaner_invalid_minified(self):
        # The minified option must be true or false
        self.assertRaises(
            ArgumentParserError,
            CSSCleaner, options={'css-cleaner-min': 'nonsense'})

    def test_cleaner_prettify(self):
        # we can get prettified HTML from CSS cleaner
        # This might result in gaps in rendered output.
        proc = CSSCleaner(options={'css-cleaner-prettify': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        with open(self.resultpath, 'rb') as fd:
            result_html = fd.read()
        assert 'seam\n   </span>\n   <span>\n    less' in result_html

    def test_cleaner_non_prettify(self):
        # we can get non-prettified HTML from CSS cleaner
        proc = CSSCleaner(options={'css-cleaner-prettify': '0'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False}, )
        with open(self.resultpath, 'rb') as fd:
            result_html = fd.read()
        assert 'seam</span><span>less text.</span>' in result_html

    def test_cleaner_non_prettify_is_default(self):
        # we get non-prettified HTML from CSS cleaner by default
        proc = CSSCleaner()
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False}, )
        with open(self.resultpath, 'rb') as fd:
            result_html = fd.read()
        assert 'seam</span><span>less text.</span>' in result_html

    def test_non_html_ignored(self):
        # Non .html/.xhtml files are ignored
        proc = CSSCleaner()
        sample_path = os.path.join(self.workdir, 'sample.txt')
        with open(sample_path, 'w') as fd:
            fd.write('Sample file.')
        self.resultpath, metadata = proc.process(
            sample_path, {'error': False})
        # input was not touched
        assert self.resultpath == sample_path

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in CSSCleaner.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {
            'css_cleaner_minified': True,
            'css_cleaner_prettify_html': False,
        }
        # explicitly set value (different from default)
        result = vars(parser.parse_args(
            [
                '-css-cleaner-min', 'no',
                '-css-cleaner-prettify', 'yes',
            ]))
        assert result == {
            'css_cleaner_minified': False,
            'css_cleaner_prettify_html': True,
        }


class TestHTMLCleanerProcessor(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.workdir2 = tempfile.mkdtemp()
        self.resultpath = None
        self.sample_path = os.path.join(self.workdir, 'sample.html')
        self.img_sample_path = os.path.join(self.workdir2, 'sample.html')
        self.img_file_path = os.path.join(
            self.workdir2, 'image_sample_html_m20918026.gif')
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
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()

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
            options={
                'html-cleaner-fix-head-nums': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()

        snippet1 = "%s" % (
            '<span class="u-o-headnum">1</span>Häding1')
        assert snippet1 in contents

    def test_option_fix_head_nums_false(self):
        # Make sure we respect the `fix_head_nums` option if false.
        proc = HTMLCleaner(
            options={
                'html-cleaner-fix-head-nums': 'False'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()

        snippet1 = "%s" % (
            '<h1 class="foo"><span class="u-o-headnum">1</span>Häding1</h1>')
        assert snippet1 not in contents

    def test_option_fix_img_links_false(self):
        # Make sure we respect the `fix_head_nums` option if true
        proc = HTMLCleaner(
            options={
                'html-cleaner-fix-img-links': '0'})
        self.resultpath, metadata = proc.process(
            self.img_sample_path, {'error': False})
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
            options={
                'html-cleaner-fix-img-links': '1'})
        self.resultpath, metadata = proc.process(
            self.img_sample_path, {'error': False})
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
            options={
                'html-cleaner-fix-sd-fields': '0'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()
        snippet = '<sdfield type="PAGE">'
        assert snippet in contents

    def test_option_fix_sdfields_true(self):
        # Make sure we respect the `fix_sdtags` option if false
        proc = HTMLCleaner(
            options={
                'html-cleaner-fix-sd-fields': '1'})
        self.resultpath, metadata = proc.process(
            self.sample_path, {'error': False})
        contents = open(self.resultpath, 'rb').read()
        snippet = '<sdfield type="PAGE">'
        assert snippet not in contents

    def test_option_invalid(self):
        # Make sure we complain when trash is set as `fix_head_nums`.
        self.assertRaises(
            ArgumentParserError,
            HTMLCleaner, options={'html-cleaner-fix-head-nums': 'foo'})
        self.assertRaises(
            ArgumentParserError,
            HTMLCleaner, options={'html-cleaner-fix-img-links': 'foo'})
        self.assertRaises(
            ArgumentParserError,
            HTMLCleaner, options={'html-cleaner-fix-sdfields': 'foo'})

    def test_rename_img_files(self):
        proc = HTMLCleaner(
            options={'html-cleaner-fix-img-links': '1'})
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
            options={'html-cleaner-fix-img-links': '1'})
        proc.rename_img_files(
            self.workdir2,
            {'not-existing-filename': 'sample_1.gif'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'sample_1.gif' not in list_dir

    def test_rename_img_files_dst_exists_already(self):
        # We cope with dest files that already exist
        proc = HTMLCleaner(
            options={'html-cleaner-fix-img-links': '1'})
        proc.rename_img_files(
            self.workdir2,
            {
                'image_sample_html_m20918026.gif':
                'image_sample_html_m20918026.gif'
            }
        )
        list_dir = os.listdir(self.workdir2)
        assert 'image_sample_html_m20918026.gif' in list_dir

    def test_rename_img_files_src_is_dir(self):
        # We cope with src files that are in fact dirs
        proc = HTMLCleaner(
            options={'html-cleaner-fix-img-links': '1'})
        os.mkdir(os.path.join(self.workdir2, 'some_dir'))
        proc.rename_img_files(
            self.workdir2,
            {'some_dir': 'sample.jpg'}
            )
        list_dir = os.listdir(self.workdir2)
        assert 'sample.jpg' not in list_dir

    def test_non_html_ignored(self):
        # Non .html/.xhtml files are ignored
        proc = HTMLCleaner()
        sample_path = os.path.join(self.workdir, 'sample.txt')
        with open(sample_path, 'w') as fd:
            fd.write('Sample file.')
        self.resultpath, metadata = proc.process(
            sample_path, {'error': False})
        # input was not touched
        assert self.resultpath == sample_path

    def test_args(self):
        # we can add create argparse-arguments from `args`
        parser = ArgumentParser()
        for arg in HTMLCleaner.args:
            parser.add_argument(
                arg.short_name, arg.long_name, **arg.keywords)
        result = vars(parser.parse_args([]))
        # defaults
        assert result == {
            'html_cleaner_fix_heading_numbers': True,
            'html_cleaner_fix_image_links': True,
            'html_cleaner_fix_sd_fields': True}
        # explicitly set value (different from default)
        result = vars(parser.parse_args([
            '-html-cleaner-fix-head-nums', '0',
            '-html-cleaner-fix-img-links', 'false',
            '-html-cleaner-fix-sd-fields', 'No']))
        assert result == {
            'html_cleaner_fix_heading_numbers': False,
            'html_cleaner_fix_image_links': False,
            'html_cleaner_fix_sd_fields': False}


class TestErrorProcessor(unittest.TestCase):

    def test_error(self):
        proc = Error()
        path, metadata = proc.process(None, {})
        assert path is None
        assert 'error-descr' in metadata.keys()
