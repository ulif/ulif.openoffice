# tests for wsgi module
import os
import pytest
import shutil
import tempfile
import unittest
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.wsgi import RESTfulDocConverter

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
            'action="http://localhost/docs"' in resp.body)
        return
