# tests for wsgi module
import os
import pytest
import shutil
import tempfile
import unittest
import zipfile
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.wsgi import RESTfulDocConverter, get_marker

pytestmark = pytest.mark.wsgi


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
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_W10')
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
            source_path=fake_src, to_cache=fake_result, suffix=marker)
        self.assertEqual('3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1', doc_id)
        doc_id = '%s_%s' % (doc_id, marker)
        url = 'http://localhost/docs/3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1'
        url = 'http://localhost/docs/%s_%s' % (
            '3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1', marker)
        req = Request.blank(url)
        resp = app(req)
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.content_type, 'application/octet-stream')
