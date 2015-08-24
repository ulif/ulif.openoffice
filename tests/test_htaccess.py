#
# test_htpasswd.py
#
# Copyright (C) 2013, 2015 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# Tests for htaccess module
import os
import tempfile
import shutil
import unittest
from base64 import b64encode
from webob import Request
from ulif.openoffice.htaccess import (
    check_credentials, HtaccessHandler, make_htaccess,
    )

PASSWDS = (
    "# comment\n"
    "bird:$apr1$MOn1SeYg$A4FLL0AuBy43RFqT2mblm0\n"
    "ornette:C7wTvLTpHi2G2\n"
    "miles:sowhat\n"
    "dizzy:{SHA}OjFPntyTrohnUIE45vd2abKu7/w=\n")


class CheckCredentialsTests(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.htaccess_path = os.path.join(self.workdir, 'sample')
        with open(self.htaccess_path, 'w') as fd:
            fd.write(PASSWDS)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_invalid_htaccess(self):
        assert False == check_credentials('foo', 'bar', 'invalid-path')

    def test_crypt(self):
        assert True == check_credentials(
            'ornette', 'wayout', self.htaccess_path, 'crypt')
        assert False == check_credentials(
            'ornette', 'waltz', self.htaccess_path, 'crypt')

    def test_plain(self):
        assert True == check_credentials(
            'miles', 'sowhat', self.htaccess_path, 'plain')
        assert False == check_credentials(
            'miles', 'polka', self.htaccess_path, 'plain')

    def test_sha1(self):
        assert True == check_credentials(
            'dizzy', 'nightintunesia', self.htaccess_path, 'sha1')
        assert False == check_credentials(
            'dizzy', 'swing', self.htaccess_path, 'sha1')

    def test_invalid_user(self):
        # non existent users can't authenticate
        assert False == check_credentials(
            'justin', 'pet', self.htaccess_path)


class TestMakeHtaccess(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.htaccess_path = os.path.join(self.workdir, 'sample')
        with open(self.htaccess_path, 'w') as fd:
            fd.write(PASSWDS)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_valid_values(self):
        handler = make_htaccess(
            None, {}, 'Sample Realm', self.htaccess_path)
        assert isinstance(handler, HtaccessHandler)

    def test_illegal_path(self):
        self.assertRaises(
            AssertionError, make_htaccess,
            None, {}, 'Sample Realm', 'not-existent-path')

    def test_invalid_auth_type(self):
        self.assertRaises(
            ValueError, make_htaccess,
            None, {}, 'Sample Realm', self.htaccess_path, 'invalid-auth')


class TestHtaccessHandler(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.htaccess_path = os.path.join(self.workdir, 'sample')
        with open(self.htaccess_path, 'w') as fd:
            fd.write(PASSWDS)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def simple_app(self, environ, start_response):
        start_response("200 OK", [("Content-type", "text/plain")])
        return ["Hello World!", ]

    def test_simple_request(self):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', self.htaccess_path)
        req = Request.blank('/')
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'
        assert ('WWW-Authenticate', 'Basic realm="Sample Realm"') in headers

    def test_send_valid_credentials(self):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', self.htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Basic %s' % (
            codecs.encode(b'miles:sowhat', 'base64').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '200 OK'
        assert body == ['Hello World!']

    def test_send_invalid_credentials(self):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', self.htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Basic %s' % (
            codecs.encode(b'miles:waltz', 'base64').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'

    def test_non_basic_auth_request(self):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', self.htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Digest %s' % (
            b64encode(b'miles:waltz').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'

    def test_remote_user_set(self):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', self.htaccess_path, 'plain')
        req = Request.blank('/')
        req.remote_user = 'miles'
        status, headers, body = req.call_application(middleware_app)
        assert status == '200 OK'
        assert body == ['Hello World!']
