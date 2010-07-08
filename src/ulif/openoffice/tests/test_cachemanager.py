##
## test_cachemanager.py
## Login : <uli@pu.smp.net>
## Started on  Wed Jul  7 15:42:51 2010 Uli Fouquet
## $Id$
## 
## Copyright (C) 2010 Uli Fouquet
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

from ulif.openoffice.cachemanager import CacheManager, Bucket

class TestCacheManager(unittest.TestCase):
    pass

class TestCacheBucket(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.workdir)
        
    def test_init(self):
        # Make sure, the dir is empty before we mess around...
        self.assertEqual([], os.listdir(self.workdir))
        
        bucket = Bucket(self.workdir)

        # Main subdirs were created...
        for subdirname in ['sources', 'results', 'data']:
            self.assertTrue(
                os.path.exists(os.path.join(self.workdir, subdirname)),
                'Not found: subdir `%s`' % subdirname
                )

        # Main attributes are set properly...
        self.assertEqual(
            bucket.srcdir, os.path.join(self.workdir, 'sources'))
        self.assertEqual(
            bucket.resultdir, os.path.join(self.workdir, 'results'))
        self.assertEqual(
            bucket._data, dict(version=0, current_num=0))

        # A bucket with same path won't overwrite existing data...
        data = bucket._getInternalData()
        self.assertEqual(data, dict(version=0, current_num=0))
        bucket._setInternalData(dict(version=0, current_num=1))
        bucket2 = Bucket(self.workdir)
        data = bucket2._getInternalData()
        self.assertEqual(data['current_num'], 1)
        return

    def test_curr_num(self):
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.getCurrentNum(), 0)
        bucket.setCurrentNum(12)
        self.assertEqual(bucket.getCurrentNum(), 12)
        return
    
def test_suite():
    return unittest.TestLoader().loadTestsFromName(
        'ulif.openoffice.tests.test_cachemanager'
        )
