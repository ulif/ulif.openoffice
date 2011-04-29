##
## testing.py
## Login : <uli@pu.smp.net>
## Started on  Fri Apr 29 15:15:44 2011 Uli Fouquet
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
"""
Test helpers.
"""
import cherrypy
import os
import shutil
import tempfile
import time
import ulif.openoffice
from webtest import TestApp
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.oooctl import check_port
from ulif.openoffice.restserver2 import Root, conf

try:
    import unittest2 as unittest
except:
    import unittest

class TestRESTfulWSGISetup(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.cachedir = tempfile.mkdtemp()
        self.access_log = os.path.join(self.workdir, 'access.log')
        self.error_log = os.path.join(self.workdir, 'error.log')
        self.cache_manager = CacheManager(self.cachedir)
        
        # configure cherrypy to be quiet ;)
        cherrypy.config.update({ "environment": "embedded" })

        cherrypy.config.update(
            {'log.access_file': self.access_log,
             'log.error_file': self.error_log,
             'log.screen': False,
             }
            )
        
        self.wsgi_app = cherrypy.Application(
            Root(cachedir=self.cachedir), '/', config=conf)
        self.app = TestApp(self.wsgi_app)

    def tearDown(self):
        shutil.rmtree(self.workdir)
        shutil.rmtree(self.cachedir)
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