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
from ulif.openoffice.restserver2 import Root, DEFAULT_CONFIG

try:
    import unittest2 as unittest
except:
    import unittest

class TestRESTfulWSGISetup(unittest.TestCase):
    """A setup that prepares a WSGI app with the RESTful cherrypy server.

    The RESTful server provided in :mod:`ulif.openoffice` is a
    cherry.py server that can also be accessed as a plain WSGI app.

    This is excellent for testing as we don't have to start a real
    webserver but can ask a locally created WSGI app directly. Tests
    are also much faster using this technique.
    
    Use `self.app` for a :mod:`webtest` based HTTP-client client.

    Use `self.wsgi_app` if you need access to the real WSGI app.
    """

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
            Root(cachedir=self.cachedir), '/', config=DEFAULT_CONFIG)
        self.app = TestApp(self.wsgi_app)

    def tearDown(self):
        shutil.rmtree(self.workdir)
        shutil.rmtree(self.cachedir)
        del self.app
        del self.wsgi_app
        return

class TestOOServerSetup(unittest.TestCase):
    """A setup that starts an OO.org server in background

    and shuts it down after tests in the accompanied test suite have
    been run.

    This setup is special in that it detects whether an instance of
    the openoffice server is already running and in that case uses
    this instance.

    For people running tests does that mean:

    - You can decrease test time (dramatically) by starting `oooctl`
      in backgroud before running tests.

    - An already running instance of OO.org server will be still
      running after tests.

    - Be prepared for slightly different test output when using an
      already running OO.org server instance.

    .. note:: This testcase works only with :mod:`unittest2`!  For
              more recent Python versions (Python >= 2.6) the default
              :mod:`unittest` module is sufficient.
    
    """
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
