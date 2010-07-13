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
import filecmp
import os
import shutil
import tempfile
import types
import unittest

from ulif.openoffice.cachemanager import CacheManager, Bucket

class CachingComponentsTestCase(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.inputdir = tempfile.mkdtemp()
        self.src_path1 = os.path.join(self.inputdir, 'srcfile1')
        self.src_path2 = os.path.join(self.inputdir, 'srcfile2')
        self.result_path1 = os.path.join(self.inputdir, 'resultfile1')
        self.result_path2 = os.path.join(self.inputdir, 'resultfile2')
        open(self.src_path1, 'wb').write('source1\n')
        open(self.src_path2, 'wb').write('source2\n')
        open(self.result_path1, 'wb').write('result1\n')
        open(self.result_path2, 'wb').write('result2\n')


class TestCacheBucket(CachingComponentsTestCase):
        
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

    def test_creation(self):
        self.assertEqual(os.listdir(self.workdir), [])
        bucket = Bucket(self.workdir)
        self.assertNotEqual(os.listdir(self.workdir), [])
        return

    def test_get_source_path(self):
        bucket = Bucket(self.workdir)
        path, marker = bucket.getSourcePath(self.src_path1)
        self.assertEqual((path, marker), (None, None))
        bucket.storeResult(self.src_path1, self.result_path1)
        bucket.storeResult(self.src_path2, self.result_path2)
        path, marker = bucket.getSourcePath(self.src_path1)
        self.assertEqual(
            (path, marker),
            (os.path.join(self.workdir, 'sources', 'source_1'), '1')
            )
        path, marker = bucket.getSourcePath(self.src_path2)
        self.assertEqual(
            (path, marker),
            (os.path.join(self.workdir, 'sources', 'source_2'), '2')
            )
        return

    def test_get_source_path_ignore_nonsense(self):
        # Nonsense files in sourcedir are ignored.
        bucket = Bucket(self.workdir)
        open(os.path.join(self.workdir, 'sources', 'source3'),
             'wb').write('Hi')
        open(os.path.join(self.workdir, 'sources', 'foo_3'),
             'wb').write('Hi')
        path, marker = bucket.getSourcePath(self.src_path1)
        self.assertEqual((path, marker), (None, None))
        bucket.storeResult(self.src_path1, self.result_path1)
        path, marker = bucket.getSourcePath(self.src_path1)
        self.assertEqual(marker, '1')
        return

    def test_get_result_path(self):
        bucket = Bucket(self.workdir)
        path = bucket.getResultPath(self.src_path1)
        self.assertEqual(path, None)
        bucket.storeResult(self.src_path1, self.result_path1)
        path = bucket.getResultPath(self.src_path1)
        self.assertNotEqual(path, None)
        bucket.storeResult(self.src_path1, self.result_path1, suffix='foo')
        path = bucket.getResultPath(self.src_path1, suffix='foo')
        self.assertTrue(path.endswith('result_1__foo'))
        path = bucket.getResultPath(self.src_path1, suffix='bar')
        self.assertEqual(path, None)
        return

    def test_store_result(self):
        bucket = Bucket(self.workdir)
        bucket.storeResult(self.src_path1, self.result_path1)
        files_are_equal = filecmp.cmp(
                self.src_path1,
                os.path.join(self.workdir, 'sources', 'source_1')
                )
        self.assertTrue(files_are_equal, msg='source files differ')
        files_are_equal = filecmp.cmp(
            self.result_path1,
            os.path.join(self.workdir, 'results', 'result_1_default')
            )
        self.assertTrue(files_are_equal, msg='result files differ')
        return

    def test_store_several_results(self):
        bucket = Bucket(self.workdir)
        bucket.storeResult(self.src_path1, self.result_path1)
        bucket.storeResult(self.src_path2, self.result_path2)
        files_are_equal = filecmp.cmp(
                self.src_path2,
                os.path.join(self.workdir, 'sources', 'source_2')
                )
        self.assertTrue(files_are_equal, msg='source files differ')
        files_are_equal = filecmp.cmp(
            self.result_path2,
            os.path.join(self.workdir, 'results', 'result_2_default')
            )
        self.assertTrue(files_are_equal, msg='result files differ')
        return

    def test_store_result_twice(self):
        bucket = Bucket(self.workdir)
        bucket.storeResult(self.src_path1, self.result_path1, suffix='foo')
        
        listing = os.listdir(os.path.join(self.workdir, 'results'))
        self.assertEqual(listing, ['result_1__foo'])
        
        bucket.storeResult(self.src_path1, self.result_path1)
        bucket.storeResult(self.src_path1, self.result_path2)
        bucket.storeResult(self.src_path1, self.result_path1)
        
        listing = os.listdir(os.path.join(self.workdir, 'results'))
        self.assertEqual(listing, ['result_1__foo', 'result_1_default'])
        
        curr_num = bucket.getCurrentNum()
        self.assertEqual(curr_num, 1)
        return
        
    def test_store_result_with_suffix(self):
        bucket = Bucket(self.workdir)
        bucket.storeResult(self.src_path1, self.result_path1, suffix='foo')
        files_are_equal = filecmp.cmp(
                self.src_path1,
                os.path.join(self.workdir, 'sources', 'source_1')
                )
        self.assertTrue(files_are_equal, msg='source files differ')
        files_are_equal = filecmp.cmp(
            self.result_path1,
            os.path.join(self.workdir, 'results', 'result_1__foo')
            )
        self.assertTrue(files_are_equal, msg='result files differ')
        return

    def test_store_result_marker(self):
        bucket = Bucket(self.workdir)
        marker = bucket.storeResult(
            self.src_path1, self.result_path1, suffix='foo')
        self.assertEqual(marker, '1')
        marker = bucket.storeResult(
            self.src_path1, self.result_path2, suffix='foo')
        self.assertEqual(marker, '1')
        marker = bucket.storeResult(
            self.src_path2, self.result_path2, suffix='foo')
        self.assertEqual(marker, '2')
        return

    # Currently disabled. It's a stress test.
    # We want a special layer for that kind of tests.
    #def test_curr_num_stress(self):
    #    bucket = Bucket(self.workdir)
    #    stressnum = 250
    #    for x in xrange(stressnum):
    #        open(os.path.join(
    #                self.inputdir, 'stressource%s' % x), 'wb').write(
    #            str(x) + '\n')
    #    self.assertEqual(len(os.listdir(self.inputdir)), stressnum+4)
    #    for x in xrange(stressnum):
    #        bucket.storeResult(
    #            os.path.join(self.inputdir, 'stressource%s' % x),
    #            self.result_path1)
    #    self.assertEqual(bucket.getCurrentNum(), stressnum)
    #    return

    def test_get_all_source_paths(self):
        bucket = Bucket(self.workdir)
        paths = bucket.getAllSourcePaths()
        self.assertTrue(
            isinstance(paths, types.GeneratorType))
        paths = list(paths)
        self.assertEqual(paths, [])
        bucket.storeResult(
            self.src_path1, self.result_path1, suffix='foo')
        paths = list(bucket.getAllSourcePaths())
        self.assertTrue(paths[0].endswith('source_1'))
        self.assertEqual(len(paths), 1)
        
        bucket.storeResult(
            self.src_path2, self.result_path2, suffix='bar')
        paths = list(bucket.getAllSourcePaths())
        self.assertEqual(len(paths), 2)
        return

    def test_get_all_source_paths_ignore_nonsense(self):
        bucket = Bucket(self.workdir)
        open(os.path.join(self.workdir, 'sources', 'source3'),
             'wb').write('Hi')
        open(os.path.join(self.workdir, 'sources', 'foo_3'),
             'wb').write('Hi')
        paths1 = list(bucket.getAllSourcePaths())
        bucket.storeResult(
            self.src_path1, self.result_path1, suffix='foo')
        paths2 = list(bucket.getAllSourcePaths())
        self.assertEqual(paths1, [])
        self.assertEqual(len(paths2), 1)

    def test_get_result_path_from_marker(self):
        bucket = Bucket(self.workdir)
        marker1 = bucket.storeResult(
            self.src_path1, self.result_path1, suffix=None)
        marker2 = bucket.storeResult(
            self.src_path1, self.result_path1, suffix='foo')
        marker3 = bucket.storeResult(
            self.src_path2, self.result_path1, suffix='foo')
        path1 = bucket.getResultPathFromMarker(marker1)
        path2 = bucket.getResultPathFromMarker(marker2, suffix='foo')
        path3 = bucket.getResultPathFromMarker(marker3, suffix='foo')
        expected_path1 = os.path.join('results', 'result_1_default')
        expected_path2 = os.path.join('results', 'result_1__foo')
        expected_path3 = os.path.join('results', 'result_2__foo')
        self.assertTrue(path1.endswith(expected_path1))
        self.assertTrue(path2.endswith(expected_path2))
        self.assertTrue(path3.endswith(expected_path3))

class TestCacheManager(CachingComponentsTestCase):

    def test_markerhandling(self):
        cm = CacheManager(self.workdir)
        marker_string = cm._composeMarker(
            'somefakedhash', 3)
        self.assertEqual(marker_string, 'somefakedhash_3')
        hash, bucket_marker = cm._dissolveMarker('somefakedhash_3')
        self.assertEqual(hash, 'somefakedhash')
        self.assertEqual(bucket_marker, '3')
        self.assertEqual(cm._dissolveMarker('asd'), (None, None))
        self.assertEqual(cm._dissolveMarker(object()), (None, None))
        return

    def test_init(self):
        cm = CacheManager(self.workdir)
        self.assertEqual(cm.level, 1)
        self.assertEqual(cm.cache_dir, self.workdir)

        cm = CacheManager(self.workdir, level=3)
        self.assertEqual(cm.level, 3)
        
        # Create cache dir if it does not exist...
        shutil.rmtree(self.workdir)
        cm = CacheManager(self.workdir)
        self.assertTrue(os.path.isdir(self.workdir))

        # If we get a file as cache dir (instead of a directory), we
        # fail loudly...
        broken_cache_dir = os.path.join(self.workdir, 'not-a-dir')
        open(broken_cache_dir, 'wb').write('i am a file')
        self.assertRaises(IOError, CacheManager, broken_cache_dir)
        return

    def test_compose_marker(self):
        cm = CacheManager(self.workdir)
        marker1 = cm._composeMarker('some_hash_digest', None)
        marker2 = cm._composeMarker('some_hash_digest', 'bucket_marker')
        self.assertEqual(marker1, 'some_hash_digest')
        self.assertEqual(marker2, 'some_hash_digest_bucket_marker')
        
    def test_get_bucket_path_from_path(self):
        cm = CacheManager(self.workdir)
        path = cm._getBucketPathFromPath(self.src_path1)
        expected_path_end = os.path.join(
            '73', '737b337e605199de28b3b64c674f9422')
        self.assertEqual(os.listdir(self.workdir), [])
        self.assertTrue(path.endswith(expected_path_end))
        return

    def test_get_bucket_path_from_hash(self):
        cm = CacheManager(self.workdir)
        hash_val = cm.getHash(self.src_path1)
        path = cm._getBucketPathFromHash(hash_val)
        expected_path_end = os.path.join(
            '73', '737b337e605199de28b3b64c674f9422')
        self.assertEqual(os.listdir(self.workdir), [])
        self.assertTrue(path.endswith(expected_path_end))

        path = cm._getBucketPathFromHash('nonsense')
        self.assertEqual(path, None)
        return
        
    def test_prepare_cache_dir(self):
        new_cache_dir = os.path.join(self.workdir, 'newcache')
        broken_cache_dir = os.path.join(self.workdir, 'broken')
        open(broken_cache_dir, 'wb').write('broken')
        cm = CacheManager(self.workdir)

        cm.cache_dir = None
        self.assertEqual(cm.prepareCacheDir(), None)
        
        cm.cache_dir = new_cache_dir
        cm.prepareCacheDir()
        self.assertTrue(os.path.isdir(new_cache_dir))
        
        cm.cache_dir = broken_cache_dir
        self.assertRaises(IOError, cm.prepareCacheDir)
        return

    def test_get_bucket_from_path(self):
        cache_dir_len1 = len(os.listdir(self.workdir))
        cm = CacheManager(self.workdir)
        bucket1 = cm.getBucketFromPath(self.src_path1)
        cache_dir_len2 = len(os.listdir(self.workdir))
        self.assertTrue(isinstance(bucket1, Bucket))
        self.assertTrue(cache_dir_len2 == cache_dir_len1+1)
        return

    def test_get_cached_file(self):
        cm = CacheManager(self.workdir)
        path = cm.getCachedFile(self.src_path1)
        self.assertTrue(path is None)
        self.assertEqual(os.listdir(self.workdir), [])

        cm.registerDoc(self.src_path1, self.result_path1, suffix=None)
        path1 = cm.getCachedFile(self.src_path1)
        path2 = cm.getCachedFile(self.src_path1, suffix='bar')
        path3 = cm.getCachedFile(self.src_path1, suffix='foo')
        self.assertTrue(path1 is not None)
        self.assertTrue(path2 is None)
        self.assertTrue(path3 is None)
        
        cm.registerDoc(self.src_path2, self.result_path1, suffix='foo')
        path1 = cm.getCachedFile(self.src_path2)
        path2 = cm.getCachedFile(self.src_path2, suffix='bar')
        path3 = cm.getCachedFile(self.src_path2, suffix='foo')
        self.assertTrue(path1 is None)
        self.assertTrue(path2 is None)
        self.assertTrue(path3 is not None)
        return

    def test_get_cached_file_from_marker(self):
        cm = CacheManager(self.workdir)
        path1 = cm.getCachedFileFromMarker('not-a-marker')
        marker1 = cm.registerDoc(
            self.src_path1, self.result_path1, suffix=None)
        path2 = cm.getCachedFileFromMarker(marker1)

        marker2 = cm.registerDoc(
            self.src_path1, self.result_path2, suffix='foo')
        path3 = cm.getCachedFileFromMarker(marker2)

        self.assertTrue(path1 is None)
        self.assertTrue(path2 is not None)
        self.assertTrue(path3 is not None)
        return
    
    def test_register_doc(self):
        pass

    def test_get_hash(self):
        pass

    def test_contains(self):
        pass

    def test_get_all_sources(self):
        pass
        
def test_suite():
    return unittest.TestLoader().loadTestsFromName(
        'ulif.openoffice.tests.test_cachemanager'
        )
