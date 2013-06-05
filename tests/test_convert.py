# tests for the convert module
import os
import shutil
import tempfile
import unittest
from ulif.openoffice.convert import convert
from ulif.openoffice.testing import TestOOServerSetup


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
        self.assertEqual(
           ['sample.pdf'], os.listdir(result_dir))
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
        self.assertEqual(
           ['sample.html'], os.listdir(result_dir))
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
            ['sample.pdf', 'sample.txt'], os.listdir(self.tmpdir))
        return

    def test_convert_fail_status_ne_zero(self):
        # if something goes wrong, we get some status != 0
        status, result_dir = convert(
            path='NoT-An-ExIsTiNg-PaTH', out_dir=self.tmpdir)
        self.assertTrue(status != 0)
        self.assertEqual([], os.listdir(self.tmpdir))
        return
