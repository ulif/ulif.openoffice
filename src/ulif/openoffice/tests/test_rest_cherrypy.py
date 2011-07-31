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
import tempfile
import zipfile
import cherrypy
try:
    import unittest2 as unittest
except:
    import unittest

from StringIO import StringIO
from ulif.openoffice.cachemanager import (
    CacheManager, CACHE_SINGLE, CACHE_PER_USER)
from ulif.openoffice.helpers import remove_file_dir
from ulif.openoffice.testing import (
    TestRESTfulWSGISetup, TestOOServerSetup
    )
from ulif.openoffice.restserver import (
    checkpassword, get_marker, get_cached_doc, cache_doc, mangle_allow_cached,
    get_cachedir, process_doc)

checkpassword_test = cherrypy.lib.auth_basic.checkpassword_dict(
    {'bird': 'bebop',
     'ornette': 'wayout',
     'testuser': 'secret',
     })

class TestRESTfulHelpers(TestOOServerSetup):

    def create_input(self):
        os.mkdir(os.path.dirname(self.input))
        open(self.input, 'wb').write('Hi there!')

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.cachedir = os.path.join(self.workdir, 'test_cache')
        os.mkdir(self.cachedir)
        self.input = os.path.join(self.workdir, 'input', 'sample.txt')
        self.create_input()
        self.output = os.path.join(self.workdir, 'output', 'sample.txt')
        os.mkdir(os.path.dirname(self.output))
        open(self.output, 'wb').write('Faked output')
        self.data = {
            'oocp.out_fmt':'html',
            'meta.procord':'unzip,oocp'
            }
        self.marker = 'WygnbWV0YS5wcm9jb3JkJywgJ3VuemlwLG9vY3AnKSwgKCd'
        self.marker += 'vb2NwLm91dF9mbXQnLCAnaHRtbCcpXQ'
        self.etag = '396199333edbf40ad43e62a1c1397793_1'
        self.resultpath = None  # For resultpaths generated in tests
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        remove_file_dir(self.resultpath)
        return

    def test_get_marker(self):
        # Make sure, sorted dicts get the same marker
        result1 = get_marker()
        result2 = get_marker(options={})
        result3 = get_marker(options={'b':'0', 'a':'1'})
        result4 = get_marker(options={'a':'1', 'b':'0'})
        assert result1 == 'W10'
        assert result2 == 'W10'
        assert result3 == result4
        assert result2 != result3

    def test_get_cached_doc_no_cachedir(self):
        # If we pass no cache dir, we get None
        result = get_cached_doc(self.input, 'nonsense', cache_dir=None)
        assert result is None

    def test_get_cached_doc_uncached(self):
        # We get None if everything is okay but the doc simply not cached
        result = get_cached_doc(self.input, 'W10', cache_dir=self.cachedir)
        assert result is None

    def test_get_cached_doc(self):
        # If a cached doc is available, we can get it from cache
        cm = CacheManager(self.cachedir)
        cm.registerDoc(
            source_path=self.input, to_cache=self.output, suffix='W10')
        path = get_cached_doc(self.input, 'W10', cache_dir=self.cachedir)
        assert isinstance(path, basestring)
        assert open(path, 'r').read() == 'Faked output'

    def test_cache_doc(self):
        # We can cache away docs
        etag = cache_doc(self.input, self.output, 'W10', self.cachedir)
        assert etag == '396199333edbf40ad43e62a1c1397793_1'
        cm = CacheManager(self.cachedir)
        cached = cm.getCachedFile(self.input, 'W10')
        assert open(cached, 'r').read() == 'Faked output'

    def test_cache_doc_wo_cachedir(self):
        # No cachedir, no caching
        etag = cache_doc(self.input, self.output, 'W10', None)
        assert etag is None

    def test_mangle_allow_cached(self):
        # Make sure we get sensible values
        result1 = mangle_allow_cached(dict(allow_cached='0'), True)
        result2 = mangle_allow_cached(dict(allow_cached='1'), True)
        result3 = mangle_allow_cached(dict(allow_cached='0'), False)
        result4 = mangle_allow_cached(dict(allow_cached='1'), False)
        result5 = mangle_allow_cached(dict(), True)
        result6 = mangle_allow_cached(dict(), False)
        result7 = mangle_allow_cached(dict(allow_cached='nonsense'), True)
        assert result1 is False
        assert result2 is True
        assert result3 is False
        assert result4 is True
        assert result5 is True
        assert result6 is False
        assert result7 is True

    def test_get_cachedir(self):
        # Make sure we get an appropriate cachedir
        result1 = get_cachedir(True, self.cachedir, CACHE_SINGLE, 'fred')
        result2 = get_cachedir(False, self.cachedir, CACHE_SINGLE, 'fred')
        result3 = get_cachedir(True, None, CACHE_SINGLE, 'fred')
        result4 = get_cachedir(True, self.cachedir, CACHE_PER_USER, 'fred')
        result5 = get_cachedir(True, self.cachedir, CACHE_PER_USER, None)
        assert result1 is not None
        assert result2 is None
        assert result3 is None
        assert result4.endswith('fred')
        assert result5 is None

    def test_process_doc(self):
        # Process uncached doc
        self.resultpath, etag, metadata, cached = process_doc(
            self.input, self.data, True, self.cachedir, CACHE_SINGLE, 'fred')
        assert etag == self.etag
        assert metadata == {'error': False, 'oocp_status': 0}
        assert cached is False
        assert '<!DOCTYPE' in open(self.resultpath, 'r').read()

    def test_process_doc_retrieve_cached(self):
        # We retrieve a cached doc if it is available
        cm = CacheManager(self.cachedir)
        cm.registerDoc(
            source_path=self.input, to_cache=self.output, suffix=self.marker)
        path, etag, metadata, cached = process_doc(
            self.input, self.data, True, self.cachedir, CACHE_SINGLE, 'fred')
        assert cached is True
        assert open(path, 'r').read() == 'Faked output'

    def test_process_doc_cached_away(self):
        # The doc gets cached if sent for the first time
        self.resultpath, etag, metadata, cached = process_doc(
            self.input, self.data, True, self.cachedir, CACHE_SINGLE, 'fred')
        self.create_input() # Processing will remove the original input
        cm = CacheManager(self.cachedir)
        path = cm.getCachedFile(self.input, self.marker)
        assert path is not None
        assert '<!DOCTYPE' in open(path, 'r').read()

    def test_process_doc_wo_cachedir(self):
        # No cachedir, no caching
        self.resultpath, etag, metadata, cached = process_doc(
            self.input, self.data, True, None, CACHE_SINGLE, 'fred')
        assert etag is None
        assert metadata == {'error': False, 'oocp_status': 0}
        assert cached is False
        assert '<!DOCTYPE' in open(self.resultpath, 'r').read()

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
