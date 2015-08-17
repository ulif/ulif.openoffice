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

    def test_simple_conversion_to_pdf(self):
        # we can convert a simple text file to pdf
        path = os.path.join(self.tmpdir, 'sample.txt')
        open(path, 'w').write('Hi there!\n')
        status, result_dir = convert(out_format='pdf', path=path)
        self.assertEqual(0, status)
        self.assertEqual(['sample.pdf'], os.listdir(result_dir))
        result_doc = open(os.path.join(result_dir, 'sample.pdf'), 'rb').read()
        self.assertEqual(result_doc[:10], b'%PDF-1.4\n%')
        shutil.rmtree(result_dir)  # clean up
        return

    def test_simple_conversion_to_html(self):
        # we can convert a simple text file to html
        path = os.path.join(self.tmpdir, 'sample.txt')
        open(path, 'w').write('Hi there!\n')
        status, result_dir = convert(out_format='html', path=path)
        self.assertEqual(0, status)
        self.assertEqual(['sample.html'], os.listdir(result_dir))
        result_doc = open(os.path.join(result_dir, 'sample.html'), 'rb').read()
        self.assertEqual(result_doc[:10], b'<!DOCTYPE ')
        shutil.rmtree(result_dir)  # clean up
        return

    def test_convert_outdir(self):
        # the outdir parameter is respected
        path = os.path.join(self.tmpdir, 'sample.txt')
        open(path, 'w').write('Hi there!\n')
        status, result_dir = convert(
            out_format='pdf', path=path, out_dir=self.tmpdir)
        self.assertEqual(0, status)
        # input and output are in the same dir
        self.assertEqual(
            ['sample.pdf', 'sample.txt'], sorted(os.listdir(self.tmpdir)))
        return

    def test_convert_fail_status_ne_zero(self):
        # if something goes wrong, we get some status != 0
        status, result_dir = convert(
            path='NoT-An-ExIsTiNg-PaTH', out_dir=self.tmpdir)
        self.assertTrue(status != 0)
        self.assertEqual([], os.listdir(self.tmpdir))
        return

    def test_convert_with_template(self):
        # we can pass in templates when converting
        doc_path = os.path.join(self.tmpdir, 'sample.txt')
        template_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample.ott')
        open(doc_path, 'w').write('Hi there!\n')
        result_path = os.path.join(self.tmpdir, 'sample.html')
        # convert with template applied
        status, result_dir = convert(
            out_format='html', path=doc_path, out_dir=self.tmpdir,
            template=template_path)
        content = open(result_path, 'rb').read()
        # tags that do not appear in un-templated docs
        assert '<pre class="western">' in content.lower()
        assert (
            '<DIV TYPE=HEADER>' in content) or (
            '<div title="header"' in content)
        return


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
