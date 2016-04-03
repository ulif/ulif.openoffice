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
import pytest
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


@pytest.fixture(scope="function")
def htaccess_path(tmpdir):
    tmpdir.join("sample").write(PASSWDS)
    return str(tmpdir.join("sample"))


class TestCheckCredentials(object):

    def test_invalid_htaccess(self):
        assert check_credentials('foo', 'bar', 'invalid-path') is False

    def test_crypt(self, htaccess_path):
        assert check_credentials(
            'ornette', 'wayout', htaccess_path, 'crypt') is True
        assert check_credentials(
            'ornette', 'waltz', htaccess_path, 'crypt') is False

    def test_plain(self, htaccess_path):
        assert check_credentials(
            'miles', 'sowhat', htaccess_path, 'plain') is True
        assert check_credentials(
            'miles', 'polka', htaccess_path, 'plain') is False

    def test_sha1(self, htaccess_path):
        assert check_credentials(
            'dizzy', 'nightintunesia', htaccess_path, 'sha1') is True
        assert check_credentials(
            'dizzy', 'swing', htaccess_path, 'sha1') is False

    def test_invalid_user(self, htaccess_path):
        # non existent users can't authenticate
        assert check_credentials(
            'justin', 'pet', htaccess_path) is False


class TestMakeHtaccess(object):

    def test_valid_values(self, htaccess_path):
        handler = make_htaccess(
            None, {}, 'Sample Realm', htaccess_path)
        assert isinstance(handler, HtaccessHandler)

    def test_illegal_path(self):
        with pytest.raises(AssertionError):
            make_htaccess(None, {}, 'Sample Realm', 'not-existent-path')

    def test_invalid_auth_type(self, htaccess_path):
        with pytest.raises(ValueError):
            make_htaccess(
                None, {}, 'Sample Realm', htaccess_path, 'invalid-auth')


class TestHtaccessHandler(object):

    def simple_app(self, environ, start_response):
        start_response("200 OK", [("Content-type", "text/plain")])
        return ["Hello World!", ]

    def test_simple_request(self, htaccess_path):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', htaccess_path)
        req = Request.blank('/')
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'
        assert ('WWW-Authenticate', 'Basic realm="Sample Realm"') in headers

    def test_send_valid_credentials(self, htaccess_path):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Basic %s' % (
            b64encode(b'miles:sowhat').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '200 OK'
        assert body == ['Hello World!']

    def test_send_invalid_credentials(self, htaccess_path):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Basic %s' % (
            b64encode(b'miles:waltz').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'

    def test_non_basic_auth_request(self, htaccess_path):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', htaccess_path, 'plain')
        req = Request.blank('/')
        req.headers['Authorization'] = 'Digest %s' % (
            b64encode(b'miles:waltz').decode('utf-8'))
        status, headers, body = req.call_application(middleware_app)
        assert status == '401 Unauthorized'

    def test_remote_user_set(self, htaccess_path):
        middleware_app = HtaccessHandler(
            self.simple_app, 'Sample Realm', htaccess_path, 'plain')
        req = Request.blank('/')
        req.remote_user = 'miles'
        status, headers, body = req.call_application(middleware_app)
        assert status == '200 OK'
        assert body == ['Hello World!']
