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
import unittest
from StringIO import StringIO
from restclient import RestClient, Resource 
from webtest import TestApp 
from ulif.openoffice.restserver2 import Root, conf

wsgi_app = None

class TestHelloWorld(unittest.TestCase):

    #layer = CherryPyServerLayer

    def setUp(self):
        # configure cherrypy to be quiet ;)
        cherrypy.config.update({ "environment": "embedded" })
        
        # Keep pyflakes happy
        self.output = StringIO()

        #self.resource = Resource('http://localhost:8080')

        self.wsgi_app = cherrypy.Application(Root(), '/', config=conf)
        self.app = TestApp(self.wsgi_app)

    def tearDown(self):
        pass

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
        self.assertEqual(headers.get('content-type', None), 'text/html')
