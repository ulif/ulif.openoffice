# tests for wsgi module
import os
import shutil
import tempfile
import unittest
from webob import Request
from ulif.openoffice.wsgi import RESTfulDocConverter


class DocConverterFunctionalTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.inputdir = os.path.join(os.path.dirname(__file__), 'input')
        self.paste_conf1 = os.path.join(self.inputdir, 'sample1.ini')

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
        from paste.deploy import loadapp
        app = loadapp(
            'config:%s' % self.paste_conf1)
        self.assertTrue(isinstance(app, RESTfulDocConverter))
        return
