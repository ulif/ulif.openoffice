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
import cherrypy
import logging
import os
import shutil
import tempfile
import time
try:
    import unittest2 as unittest
except:
    import unittest
import ulif.openoffice
from ulif.openoffice.oooctl import check_port
from StringIO import StringIO
from restclient import RestClient, Resource 
from webtest import TestApp 
from ulif.openoffice.restserver2 import Root, conf
from ulif.openoffice.tests.test_ulifopenoffice import setUp

wsgi_app = None

class TestRESTfulWSGILayer(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.access_log = os.path.join(self.workdir, 'access.log')
        self.error_log = os.path.join(self.workdir, 'error.log')
        
        # configure cherrypy to be quiet ;)
        cherrypy.config.update({ "environment": "embedded" })

        cherrypy.config.update(
            {'log.access_file': self.access_log,
             'log.error_file': self.error_log,
             'log.screen': False,
             }
            )
        
        # Keep pyflakes happy
        #self.output = StringIO()

        #self.resource = Resource('http://localhost:8080')

        self.wsgi_app = cherrypy.Application(Root(), '/', config=conf)
        self.app = TestApp(self.wsgi_app)

    def tearDown(self):
        shutil.rmtree(self.workdir)
        del self.app
        del self.wsgi_app
        return

class TestRESTfulFunctionalSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set clean HOME environment as OOO.org might scan it...
        cls._marker = object()
        cls.old_home = os.environ.get('HOME', cls._marker)
        cls.homedir = tempfile.mkdtemp()
        os.environ['HOME'] = cls.homedir

        # Don't start oooctl if it runs already...
        cls.ooo_running = False
        if check_port('localhost', 2002):
            cls.ooo_running = True
            return

        # Start oooctl...
        path = os.path.dirname(ulif.openoffice.__file__)
        cls.oooctl_path = os.path.abspath(os.path.join(
                path, '..', '..', '..', 'bin', 'oooctl'))
        os.system(cls.oooctl_path + ' --stdout=/tmp/oooctl.log start')
        time.sleep(3)
        return

    @classmethod
    def tearDownClass(cls):
        # Only shut down oooctl if it were not running already...
        if cls.ooo_running is not True:
            os.system(cls.oooctl_path + ' stop')

        # Clean up dirs...
        shutil.rmtree(cls.homedir)

        # Set HOME to old state...
        if cls.old_home is cls._marker:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = cls.old_home

        return


class TestRESTful(TestRESTfulWSGILayer):

    def test_foo(self):
        response = self.app.get('/index')
        self.assertTrue(response.body.startswith('<html>'))
        pass

    def test_status_200(self):
        response = self.app.get('/sidewinder')
        self.assertEqual(response.status, '200 OK')
        return

    def test_header_item(self):
        response = self.app.get('/sidewinder')
        headers = response.headers
        self.assertTrue('content-type' in headers)
        assert headers.get('content-type', None) == 'text/html;charset=utf-8'
        #self.assertEqual(headers.get('content-type', None), 'text/html')

    def test_POST(self):
        response = self.app.post(
            '/pdf',
            params={'var1':'value1'}, headers=None, extra_environ=None,
            #status=None, content_type="text/html",
            #upload_files = [('document', 'sample.txt', 'somecontent')],
            upload_files = [
                ('document', 'sample.txt', 'Some\nContent.\n'),
                ('document2', 'sample2.txt', 'Some\nMore\nContent.\n'),
                ],
            )
        #    )
        #, upload_files=[
        #        ('document', 'sample.txt', u'Some\nContent.\n'),
        #        ])
        #print response.body
        body = response.body
        headers = response.headers
        #assert body == 'asd'
        #self.assertEqual(1, 1)


class TestRESTfulFunctional(TestRESTfulWSGILayer, TestRESTfulFunctionalSetup):
    def setUp(self):
        super(TestRESTfulFunctional, self).setUp()
        self.resultdir = None
        return

    def tearDown(self):
        if self.resultdir is not None:
            if not os.path.isdir(self.resultdir):
                self.resultdir = os.path.dirname(self.resultdir)
            if os.path.isdir(self.resultdir):
                shutil.rmtree(self.resultdir)
        super(TestRESTfulFunctional, self).tearDown()
        return

    def test_foo(self):
        from ulif.openoffice.convert import convert_to_html
        src_file = os.path.join(self.workdir, 'mytest.txt')
        open(src_file, 'wb').write('Some sample\nwith 2 lines')
        status, paths = convert_to_html(path=src_file)
        path = paths[0]
        basename = os.path.basename(path)
        assert self.resultdir is None
        self.resultdir = path
        assert basename == u'mytest.html'
        return

    def test_POST(self):
        response = self.app.post(
            '/docs',
            params={'doc_id':'12'},
            )
        #    upload_files = [
        #        ('document', 'sample.txt', 'Some\nContent.\n'),
        #        ('document2', 'sample2.txt', 'Some\nMore\nContent.\n'),
        #        ],
        #    )
        body = response.body
        headers = response.headers
        assert body == 'asd'

    def test_POST2(self):
        response = self.app.post(
            '/docs',
            upload_files = [
                ('doc', 'sample.txt', 'Some\nContent.\n'),
                ],
            )
        body = response.body
        headers = response.headers
        assert body == 'asd'
