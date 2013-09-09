# tests for xmlrpc module
import os
import shutil
import tempfile
import unittest
import xmlrpclib
from StringIO import StringIO
from mimetools import Message
from webob import Request
from ulif.openoffice.xmlrpc import WSGIXMLRPCApplication


class ServerTestsSetup(unittest.TestCase):
    # common setup for XMLRPC server tests

    def setUp(self):
        self.src_dir = tempfile.mkdtemp()
        self.src_path = os.path.join(self.src_dir, 'sample.txt')
        open(self.src_path, 'wb').write('Hi there!\n')
        self.result_dir = None

    def tearDown(self):
        shutil.rmtree(self.src_dir)
        if self.result_dir is not None and os.path.isdir(self.result_dir):
            shutil.rmtree(self.result_dir)


class ServerTests(ServerTestsSetup):
    # raw xmlrpc server tests

    def xmlrpc_request(self, method_name, args=()):
        # create an xmlrpcrequest
        request = Request.blank('http://localhost/RPC2')
        request.method = 'POST'
        request.content_type = 'text/xml'
        request.body = xmlrpclib.dumps(args, method_name, allow_none=True)
        return request

    def test_http_get_not_accepted(self):
        # HTTP GET is not acceptable for xmlrpc
        app = WSGIXMLRPCApplication()
        req = Request.blank('http://localhost/test.html')
        resp = req.get_response(app)
        self.assertEqual(resp.status, '400 Bad Request')

    def test_help_available(self):
        # we can request a list of messages
        app = WSGIXMLRPCApplication()
        req = self.xmlrpc_request('system.listMethods', ())
        resp = req.get_response(app)
        assert resp.body.startswith("<?xml version='1.0'?>")
        assert "<string>system.methodHelp</string>" in resp.body
        # the result can be processed by xmlrpclib
        result = xmlrpclib.loads(resp.body)
        assert isinstance(result, tuple)
        result_values, method_name = result
        assert 'convert_locally' in result_values[0]

    def test_convert_locally(self):
        # we can convert files locally
        app = WSGIXMLRPCApplication()
        req = self.xmlrpc_request(
            'convert_locally', (self.src_path, {}, None))
        resp = req.get_response(app)
        result = xmlrpclib.loads(resp.body)
        result_path, cache_dir, metadata = result[0][0]
        self.result_dir = os.path.dirname(result_path)   # for cleanup
        assert metadata['error'] is False


class HTTPWSGIResponse(object):

    def __init__(self, webob_resp):
        self.resp = webob_resp
        self._body = StringIO(self.resp.body)
        self._body.seek(0)
        self.reason = self.resp.status.split(" ", 1)
        self.status = self.resp.status_int

    def read(self, amt=None):
        return self._body.read()

    def getheader(self, name, default=None):
        return self.resp.headers.get(name, default)

    def msg(self):
        return Message(StringIO(self.resp.__str__()))


class WSGILikeHTTP(object):

    def __init__(self, host, app):
        self.app = app
        self.headers = {}
        self.content = StringIO()

    def putrequest(self, method, handler, **kw):
        self.method = method
        self.handler = handler

    def putheader(self, key, value):
        self.headers[key] = value

    def endheaders(self, body, *args):
        self.body = body

    def getresponse(self, buffering=True):
        req = Request.blank(self.handler)
        for key, val in self.headers.items():
            req.headers[key] = val
        req.method = self.method
        req.body = self.body
        resp = req.get_response(self.app)
        return HTTPWSGIResponse(resp)


class WSGIAppTransport(xmlrpclib.Transport):
    def __init__(self, app):
        xmlrpclib.Transport.__init__(self)
        self.app = app

    def make_connection(self, host):
        host, extra_headers, x509 = self.get_host_info(host)
        return WSGILikeHTTP(host, self.app)


class ServerProxyTests(ServerTestsSetup):
    # xmlrpcapplication tests that use an xmlrpclib.ServerProxy

    def setUp(self):
        super(ServerProxyTests, self).setUp()
        self.app = WSGIXMLRPCApplication()
        self.proxy = xmlrpclib.ServerProxy(
            'http://admin:admin@dummy/',
            transport=WSGIAppTransport(self.app))

    def test_convert_locally(self):
        # we can convert docs locally
        result_path, cache_key, metadata = self.proxy.convert_locally(
            self.src_path, {})
        self.result_dir = os.path.dirname(result_path)
        assert result_path.endswith('/sample.html.zip')

    def test_convert_locally_in_list_methods(self):
        # we can list methods (and convert_locally is included)
        result = self.proxy.system.listMethods()
        assert isinstance(result, list)
        assert 'convert_locally' in result
