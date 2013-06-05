##
## test_resources.py
##
## Copyright (C) 2011, 2013 Uli Fouquet
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
import tempfile
from ulif.openoffice.resource import create_resource
from ulif.openoffice.testing import TestOOServerSetup


class TestResources(TestOOServerSetup):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.cachedir = tempfile.mkdtemp()
        self.samplefile = os.path.join(self.workdir, 'sample.txt')
        open(self.samplefile, 'wb').write('Some sample text\n')
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        shutil.rmtree(self.cachedir)
        return

    def remove_resultfiles(self, path):
        dir_to_remove = path
        if path is None:
            return
        if os.path.isfile(path):
            dir_to_remove = os.path.dirname(path)
        if os.path.isdir(dir_to_remove):
            shutil.rmtree(dir_to_remove)
        return

    def test_create_none(self):
        # If we pass no file, we will get no result
        status, hash, path = create_resource(None)
        assert status != 0
        assert hash is None
        assert path is None

    def test_create_invalid(self):
        # If we pass an unprocessable doc, we will get no result
        invalid_stuff = os.path.join(self.workdir, 'trash.ill')
        status, hash, path = create_resource(invalid_stuff)
        self.remove_resultfiles(path)
        assert status != 0
        assert hash is None
        assert path is None

    def test_create_simple_got_file(self):
        # If we give no further parameters, we will get a document...
        status, hash, path = create_resource(self.samplefile)
        assert os.path.isfile(path)
        self.remove_resultfiles(path)
        return
