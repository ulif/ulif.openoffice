##
## test_helpers.py
## Login : <uli@pu.smp.net>
## Started on  Mon May  2 00:53:37 2011 Uli Fouquet
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
import tempfile
import unittest
from ulif.openoffice.processor import OOConvProcessor
from ulif.openoffice.helpers import (
    copy_to_secure_location, get_entry_points, unzip)

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        path = self.resultpath
        if isinstance(path, basestring):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            shutil.rmtree(path)
        return
    
    def test_copy_to_secure_location_file(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        self.resultpath = copy_to_secure_location(sample_path)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_copy_to_secure_location_path(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        sample_dir = os.path.dirname(sample_path)
        self.resultpath = copy_to_secure_location(sample_dir)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_get_entry_points(self):
        result = get_entry_points('ulif.openoffice.processors')
        assert result['oocp'] is OOConvProcessor

    def test_unzip(self):
        # make sure we can unzip filetrees
        zipfile = os.path.join(self.workdir, 'sample.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            zipfile)
        dst = os.path.join(self.workdir, 'dst')
        os.mkdir(dst)
        unzip(zipfile, dst)
        assert os.listdir(dst) == ['somedir']
        level2_dir = os.path.join(dst, 'somedir')
        assert os.listdir(level2_dir) == ['sample.txt', 'othersample.txt']
