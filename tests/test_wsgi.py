# tests for wsgi module
import os
import pytest
import shutil
import tempfile
import unittest
import zipfile
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.wsgi import (
    RESTfulDocConverter, get_marker, FileIterator, FileIterable,
    )

pytestmark = pytest.mark.wsgi


class FileIteratorTests(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.path = os.path.join(self.workdir, 'iter.test')
        open(self.path, 'wb').write(b'0123456789')  # prepopulate

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_empty_file(self):
        open(self.path, 'wb').write('')
        fi = FileIterator(self.path, None, None)
        self.assertRaises(StopIteration, next, iter(fi))

    def test_start(self):
        fi = FileIterator(self.path, 4, None)
        self.assertEqual(b'456789', next(fi))
        self.assertRaises(StopIteration, next, fi)

    def test_stop(self):
        fi = FileIterator(self.path, 0, 4)
        self.assertEqual(b'0123', next(fi))
        self.assertRaises(StopIteration, next, fi)

    def test_start_and_stop(self):
        fi = FileIterator(self.path, 2, 6)
        self.assertEqual(b'2345', next(fi))
        self.assertRaises(StopIteration, next, fi)

    def test_multiple_reads(self):
        block = b'x' * FileIterator.chunk_size
        open(self.path, 'wb').write(2 * block)
        fi = FileIterator(self.path)
        self.assertEqual(block, next(fi))
        self.assertEqual(block, next(fi))
        self.assertRaises(StopIteration, next, fi)

    def test_start_bigger_than_end(self):
        fi = FileIterator(self.path, 2, 1)
        self.assertRaises(StopIteration, next, fi)

    def test_end_is_zero(self):
        fi = FileIterator(self.path, 0, 0)
        self.assertRaises(StopIteration, next, fi)


class FileIterableTests(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.path = os.path.join(self.workdir, 'myfile.doc')

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_range(self):
        # we can get a range
        open(self.path, 'wb').write(b'0123456789')
        fi = FileIterable(self.path)
        self.assertEqual([b'234'], list(fi.app_iter_range(2, 5)))
        self.assertEqual([b'67'], list(fi.app_iter_range(6, 8)))


class DocConverterFunctionalTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.cachedir = os.path.join(self.workdir, 'cache')
        self.inputdir = os.path.join(os.path.dirname(__file__), 'input')
        self.paste_conf1 = os.path.join(self.inputdir, 'sample1.ini')
        self.paste_conf2 = os.path.join(self.inputdir, 'sample2.ini')
        # create local paste conf with local cachedir set
        self.paste_conf_tests = os.path.join(self.workdir, 'paste.ini')
        paste_conf = open(self.paste_conf2, 'r').read().replace(
            '/tmp/mycache', self.cachedir)
        open(self.paste_conf_tests, 'w').write(paste_conf)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_restful_doc_converter(self):
        # we can create a RESTful sample app
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/test.html')
        resp = app(req)
        self.assertEqual(resp.status, '404 Not Found')
        return

    def test_restful_doc_converter_simple_get(self):
        # RESTful sample app handles simple GET
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        self.assertEqual(resp.status, '200 OK')
        return

    def test_paste_deploy_loader(self):
        # we can find the docconverter via paste.deploy plugin
        app = loadapp('config:%s' % self.paste_conf1)
        self.assertTrue(isinstance(app, RESTfulDocConverter))
        self.assertTrue(app.cache_dir is None)
        return

    def test_paste_deploy_options(self):
        # we can set options via paste.deploy
        app = loadapp('config:%s' % self.paste_conf_tests)
        self.assertTrue(isinstance(app, RESTfulDocConverter))
        self.assertEqual(app.cache_dir, self.cachedir)
        return

    def test_new(self):
        # we can get a form for sending new docs
        app = RESTfulDocConverter(cache_dir=self.cachedir)
        req = Request.blank('http://localhost/docs/new')
        resp = app(req)
        self.assertEqual(resp.headers['Content-Type'],
                         'text/html; charset=UTF-8')
        self.assertTrue(
            'action="/docs"' in resp.body)
        return

    def test_create_with_cache(self):
        # we can trigger conversions that will be cached
        app = RESTfulDocConverter(cache_dir=self.cachedir)
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        # we get a location header
        location = resp.headers['Location']
        self.assertEqual(
            location,
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_1')
        self.assertEqual(resp.status, '201 Created')
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        content_file = os.path.join(self.workdir, 'myresult.zip')
        open(content_file, 'w').write(resp.body)
        self.assertTrue(zipfile.is_zipfile(content_file))
        myzipfile = zipfile.ZipFile(content_file, 'r')
        self.assertTrue('sample.html' in myzipfile.namelist())
        return

    def test_create_without_cache(self):
        # we can convert docs without cache but won't get a GET location
        app = RESTfulDocConverter(cache_dir=None)
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        # we get a location header
        self.assertTrue('Location' not in resp.headers)
        # instead of 201 Created we get 200 Ok
        self.assertEqual(resp.status, '200 OK')
        # we get a readable ZIP file
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        content_file = os.path.join(self.workdir, 'myresult.zip')
        open(content_file, 'w').write(resp.body)
        self.assertTrue(zipfile.is_zipfile(content_file))
        myzipfile = zipfile.ZipFile(content_file, 'r')
        self.assertTrue('sample.html' in myzipfile.namelist())
        return

    def test_show_with_cache(self):
        # we can retrieve cached files
        app = RESTfulDocConverter(cache_dir=self.cachedir)
        fake_src = os.path.join(self.workdir, 'sample_in.txt')
        fake_result = os.path.join(self.workdir, 'sample_out.pdf')
        open(fake_src, 'w').write('Fake source.')
        open(fake_result, 'w').write('Fake result.')
        marker = get_marker(dict(foo='bar', bar='baz'))
        doc_id = app.cache_manager.register_doc(
            source_path=fake_src, to_cache=fake_result, repr_key=marker)
        self.assertEqual('3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1', doc_id)
        doc_id = '%s_%s' % (doc_id, marker)
        url = 'http://localhost/docs/3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        req = Request.blank(url)
        resp = app(req)
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.content_type, 'application/pdf')
