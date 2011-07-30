##
## test_rest_cherrypy.py
## Login : <uli@pu.smp.net>
## Started on  Wed Apr 20 10:58:23 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
import base64
import os
import shutil
import zipfile
import cherrypy
try:
    import unittest2 as unittest
except:
    import unittest

from StringIO import StringIO
from ulif.openoffice.testing import (
    TestRESTfulWSGISetup, TestOOServerSetup
    )
from ulif.openoffice.restserver import checkpassword

checkpassword_test = cherrypy.lib.auth_basic.checkpassword_dict(
    {'bird': 'bebop',
     'ornette': 'wayout',
     'testuser': 'secret',
     })

class TestRESTful(TestRESTfulWSGISetup):

    def tearDown(self):
        super(TestRESTful, self).tearDown()
        # Disable authentication
        cherrypy.config.update({'tools.auth_basic.on': False,})
        return

    def test_POST_no_doc(self):
        # If we do not pass a doc parameter, this is a bad request
        response = self.app.post(
            '/docs',
            params={'meta.procord':'oocp,zip'},
            expect_errors = True,
            )
        assert response.status == '400 Bad Request'

    def test_POST_doc_not_a_file(self):
        # If the doc parameter is not a file, this is a bad request
        response = self.app.post(
            '/docs',
            params={'doc':'some_string'},
            expect_errors = True,
            )
        assert response.status == '400 Bad Request'

    def test_POST_unauthorized(self):
        # When basic auth is enabled, we cannot post docs.
        cherrypy.config.update({'tools.auth_basic.on': True,})
        response = self.app.post(
            '/docs',
            params={'doc':'some_string'},
            expect_errors = True,
            )
        cherrypy.config.update({'tools.auth_basic.on': False,})
        assert response.status == '401 Unauthorized'

    def test_POST_invalid_creds(self):
        # Invalid credentials will be noticed.
        cherrypy.config.update({'tools.auth_basic.on': True,})
        self.wsgi_app.config['/'].update(
            {'tools.auth_basic.checkpassword': checkpassword_test,
             })
        response = self.app.post(
            '/docs',
            headers = [
                ('Authorization', 'Basic %s' %(
                        base64.encodestring('testuser:nonsense')[:-1])),
                ],
            params={'doc':'some_string'},
            expect_errors = True,
            )
        cherrypy.config.update({'tools.auth_basic.on': False,})
        assert response.status == '401 Unauthorized'

    def test_GET_state_authorized(self):
        # We can get a status report
        cherrypy.config.update({'tools.auth_basic.on': True,})
        self.wsgi_app.config['/'].update(
            {'tools.auth_basic.checkpassword': checkpassword_test,
             })
        response = self.app.get(
            '/status',
            headers = [
                ('Authorization',
                 'Basic %s' % 'testuser:secret'.encode('base64'))],
            )
        assert '<h1>Status Report</h1>' in response.body

    def test_GET_state_unauthorized(self):
        # We cannot get a status report if unauthorized
        cherrypy.config.update({'tools.auth_basic.on': True,})
        self.wsgi_app.config['/'].update(
            {'tools.auth_basic.checkpassword': checkpassword_test,
             })
        response = self.app.get(
            '/status',
            headers = [
                ('Authorization',
                 'Basic %s' % 'testuser:nonsense'.encode('base64'))],
            expect_errors = True,
            )
        assert response.status == '401 Unauthorized'


class TestRESTfulFunctional(TestRESTfulWSGISetup, TestOOServerSetup):
    def setUp(self):
        super(TestRESTfulFunctional, self).setUp()
        self.resultdir = None
        return

    def tearDown(self):
        cherrypy.config.update(
            {'tools.auth_basic.on': False,
             })
        if self.resultdir is not None:
            if not os.path.isdir(self.resultdir):
                self.resultdir = os.path.dirname(self.resultdir)
            if os.path.isdir(self.resultdir):
                shutil.rmtree(self.resultdir)
        super(TestRESTfulFunctional, self).tearDown()
        return

    def test_POST_oocp_only(self):
        response = self.app.post(
            '/docs',
            params={'meta.procord':'oocp'},
            upload_files = [
                ('doc', 'sample.txt', 'Some\nContent.\n'),
                ],
            )
        body = response.body
        headers = response.headers
        assert body.startswith('<!DOCTYPE HTML')

    def test_POST_complex(self):
        src = os.path.join(os.path.dirname(__file__), 'input', 'testdoc1.doc')
        response = self.app.post(
            '/docs',
            params={'meta.procord':'oocp,tidy,css_cleaner,zip'},
            upload_files = [
                ('doc', 'testdoc1.doc', open(src, 'rb').read()),
                ],
            )
        body = response.body
        headers = response.headers
        zip_file = zipfile.ZipFile(StringIO(body), 'r')
        file_list = zip_file.namelist()
        assert 'testdoc1.html' in file_list
        assert 'testdoc1.css' in file_list

    def test_POST_authorized(self):
        # When basic auth is enabled, we can post docs.
        cherrypy.config.update(
            {'tools.auth_basic.on': True,
             })
        self.wsgi_app.config['/'].update(
            {'tools.auth_basic.checkpassword': checkpassword_test,
             })
        response = self.app.post(
            '/docs',
            headers = [
                ('Authorization', 'Basic %s' %(
                        base64.encodestring('testuser:secret')[:-1])),
                ],
            upload_files = [
                ('doc', 'sample.txt', 'Some\nContent.\n'),
                ],
            )
        body = response.body
        assert 'Unauthorized' not in body

    def test_POST_error(self):
        # When the pipeline returns no result, we return any error-msg.
        response = self.app.post(
            '/docs',
            params={'meta.procord': 'error'},
            upload_files = [
                ('doc', 'sample.txt', 'Some\nContent.\n'),
                ],
            expect_errors = True,
            )
        status = response.status
        assert status == '503 Service Unavailable'
        assert 'Intentional error' in response.body

    def test_POST_CACHED(self):
        # We can request cached results
        response = self.app.post(
            '/docs',
            params={'meta.procord':'oocp', 'allow_cached': '1'},
            upload_files = [
                ('doc', 'sample.txt', 'Some\nContent.\n'),
                ],
            expect_errors = True,
            )
        body = response.body
        assert body == 'asd'
        headers = response.headers
        assert body.startswith('<!DOCTYPE HTML')
