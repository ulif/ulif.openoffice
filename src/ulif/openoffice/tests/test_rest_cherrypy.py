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
import os
import shutil
try:
    import unittest2 as unittest
except:
    import unittest

from ulif.openoffice.testing import (
    TestRESTfulWSGISetup, TestRESTfulFunctionalSetup
    )

class TestRESTful(TestRESTfulWSGISetup):

    def NOtest_foo(self):
        response = self.app.get('/index')
        self.assertTrue(response.body.startswith('<html>'))
        pass

    def NOtest_status_200(self):
        response = self.app.get('/sidewinder')
        self.assertEqual(response.status, '200 OK')
        return

    def NOtest_header_item(self):
        response = self.app.get('/sidewinder')
        headers = response.headers
        self.assertTrue('content-type' in headers)
        assert headers.get('content-type', None) == 'text/html;charset=utf-8'
        #self.assertEqual(headers.get('content-type', None), 'text/html')

    def NOtest_POST(self):
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


class TestRESTfulFunctional(TestRESTfulWSGISetup, TestRESTfulFunctionalSetup):
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

    def NOtest_POST(self):
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
