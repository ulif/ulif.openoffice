# tests for wsgi module
import unittest
from webob import Request
from ulif.openoffice.wsgi import RESTfulDocConverter


class DocConverterFunctionalTestCase(unittest.TestCase):

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
