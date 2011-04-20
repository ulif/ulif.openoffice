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
from StringIO import StringIO
from restclient import RestClient, Resource 
import cherrypy
import unittest
 
from ulif.openoffice.restserver2 import Root, conf

class TestHelloWorld(unittest.TestCase):
    def setUp(self):
        # configure cherrypy to be quiet ;)
        cherrypy.config.update({ "environment": "embedded" })

        # get WSGI app.
        self.wsgi_app = cherrypy.tree.mount(Root(), '/', config=conf)

        # initialize
        cherrypy.server.start()

        # Keep pyflakes happy
        self.output = StringIO()

        self.resource = Resource('http://localhost:8080')

    def tearDown(self):
        # shut down the cherrypy server.
        cherrypy.server.stop()

    def test_foo(self):
        pass

    def test_bar(self):
        page = self.resource.get('/sidewinder')
        response = self.resource.get_response()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.items(), 'asd')
        self.assertEqual(dir(resource.get_response()), 'asd')
        return 
    
    def test_status_200(self):
        page = self.resource.get('/sidewinder')
        response = self.resource.get_response()
        self.assertEqual(response.status, 200)
        return

    def test_header_item(self):
        page = self.resource.get('/sidewinder')
        response = self.resource.get_response()
        headers = dict(response.items())
        self.assertTrue('content-type' in headers.keys())
        self.assertEqual(headers.get('content-type', None), 'text/html')
