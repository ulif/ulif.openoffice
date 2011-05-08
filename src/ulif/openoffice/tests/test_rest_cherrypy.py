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
import zipfile
try:
    import unittest2 as unittest
except:
    import unittest

from StringIO import StringIO
from ulif.openoffice.testing import (
    TestRESTfulWSGISetup, TestOOServerSetup
    )

class TestRESTful(TestRESTfulWSGISetup):

    def test_POST_no_doc(self):
        # If we do not pass a doc parameter, this is a bad request
        response = self.app.post(
            '/docs',
            params={'meta.procord':'oocp,zip'},
            expect_errors = True,
            )
        assert response.status == '400 Bad Request'


class TestRESTfulFunctional(TestRESTfulWSGISetup, TestOOServerSetup):
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
            params={'meta.procord':'oocp,zip'},
            upload_files = [
                ('doc', 'testdoc1.doc', open(src, 'rb').read()),
                ],
            )
        body = response.body
        headers = response.headers
        zip_file = zipfile.ZipFile(StringIO(body), 'r')
        file_list = zip_file.namelist()
        assert 'testdoc1.html' in file_list
