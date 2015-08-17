# tests for the convert module
import os
import pytest
import shutil
import tempfile
from ulif.openoffice.convert import convert, exec_cmd
from ulif.openoffice.testing import TestOOServerSetup

pytestmark = pytest.mark.converter


class ConvertTests(TestOOServerSetup):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        return

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestConvert(object):

    def test_convert_no_path(self, run_lo_server):
        # w/o a path we get no conversion
        assert (None, None) == convert()

    def test_exec_cmd(self, envpath_no_venv):
        # we can exec commands and get the output back
        status, output = exec_cmd('unoconv --help')
        assert status == 1
        assert output[:84] == (
            b'usage: unoconv [options] file [file2 ..]\n'
            b'Convert from and to any format supported by')

    def test_simple_conversion_to_pdf(self, run_lo_server, tmpdir):
        # we can convert a simple text file to pdf
        path = tmpdir.join('sample.txt')
        path.write('Hi there!\n')
        status, result_dir = convert(out_format='pdf', path=str(path))
        assert status == 0
        assert os.listdir(result_dir) == ['sample.pdf']
        result_doc = open(os.path.join(result_dir, 'sample.pdf'), 'rb').read()
        assert result_doc.startswith(b'%PDF-1.4\n%')
        shutil.rmtree(result_dir)  # clean up
        return

    def test_simple_conversion_to_html(self, run_lo_server, tmpdir):
        # we can convert a simple text file to html
        path = tmpdir.join('sample.txt')
        path.write('Hi there!\n')
        status, result_dir = convert(out_format='html', path=str(path))
        assert status == 0
        assert os.listdir(result_dir) == ['sample.html']
        result_doc = open(os.path.join(result_dir, 'sample.html'), 'rb').read()
        assert result_doc.startswith(b'<!DOCTYPE ')
        shutil.rmtree(result_dir)  # clean up
        return

    def test_convert_outdir(self, run_lo_server, tmpdir):
        # the outdir parameter is respected
        path = tmpdir.join('sample.txt')
        path.write('Hi there!\n')
        status, result_dir = convert(
            out_format='pdf', path=str(path), out_dir=str(tmpdir))
        assert status == 0
        # input and output are in the same dir
        assert sorted(os.listdir(str(tmpdir))) == ['sample.pdf', 'sample.txt']

    def test_convert_fail_status_ne_zero(self, run_lo_server, tmpdir):
        # if something goes wrong, we get some status != 0
        status, result_dir = convert(
            path='NoT-An-ExIsTiNg-PaTH', out_dir=str(tmpdir))
        assert status != 0
        assert os.listdir(str(tmpdir)) == []

    def test_convert_with_template(self, run_lo_server, tmpdir):
        # we can pass in templates when converting
        doc_path = tmpdir.join('sample.txt')
        doc_path.write('Hi there!\n')
        template_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample.ott')
        # convert with template applied
        status, result_dir = convert(
            out_format='html', path=str(doc_path), out_dir=str(tmpdir),
            template=template_path)
        content = tmpdir.join('sample.html').read()
        # tags that do not appear in un-templated docs
        assert '<pre class="western">' in content.lower()
        assert (
            '<DIV TYPE=HEADER>' in content) or (
            '<div title="header"' in content)
