import filecmp
import os
import pytest
import shutil
import tempfile
import types
import unittest
from ulif.openoffice.cachemanager import CacheManager, Bucket

pytestmark = pytest.mark.cachemanager


class CachingComponentsTestCase(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.inputdir = tempfile.mkdtemp()
        self.src_path1 = os.path.join(self.inputdir, 'srcfile1')
        self.src_path2 = os.path.join(self.inputdir, 'srcfile2')
        self.result_path1 = os.path.join(self.inputdir, 'resultfile1')
        self.result_path2 = os.path.join(self.inputdir, 'resultfile2')
        self.result_path3 = os.path.join(self.inputdir, 'resultfile3')
        self.result_path4 = os.path.join(self.inputdir, 'resultfile4')
        open(self.src_path1, 'w').write('source1\n')
        open(self.src_path2, 'w').write('source2\n')
        open(self.result_path1, 'w').write('result1\n')
        open(self.result_path2, 'w').write('result2\n')
        open(self.result_path3, 'w').write('result3\n')
        open(self.result_path4, 'w').write('result4\n')

    def tearDown(self):
        shutil.rmtree(self.workdir)
        shutil.rmtree(self.inputdir)


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
        data = bucket._get_internal_data()
        self.assertEqual(data, dict(version=0, current_num=0))
        bucket._set_internal_data(dict(version=0, current_num=1))
        bucket2 = Bucket(self.workdir)
        data = bucket2._get_internal_data()
        self.assertEqual(data['current_num'], 1)
        return

    def test_curr_num(self):
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.get_current_num(), 0)
        bucket.set_current_num(12)
        self.assertEqual(bucket.get_current_num(), 12)
        return

    def test_creation(self):
        self.assertEqual(os.listdir(self.workdir), [])
        Bucket(self.workdir)
        self.assertNotEqual(os.listdir(self.workdir), [])
        return

    def test_get_source_path(self):
        bucket = Bucket(self.workdir)
        path, marker = bucket.get_source_path(self.src_path1)
        self.assertEqual((path, marker), (None, None))
        bucket.store_result(self.src_path1, self.result_path1)
        bucket.store_result(self.src_path2, self.result_path2)
        path, marker = bucket.get_source_path(self.src_path1)
        self.assertEqual(
            (path, marker),
            (os.path.join(self.workdir, 'sources', 'source_1'), '1')
            )
        path, marker = bucket.get_source_path(self.src_path2)
        self.assertEqual(
            (path, marker),
            (os.path.join(self.workdir, 'sources', 'source_2'), '2')
            )
        return

    def test_get_source_path_ignore_nonsense(self):
        # Nonsense files in sourcedir are ignored.
        bucket = Bucket(self.workdir)
        open(os.path.join(self.workdir, 'sources', 'source3'),
             'w').write('Hi')
        open(os.path.join(self.workdir, 'sources', 'foo_3'),
             'w').write('Hi')
        path, marker = bucket.get_source_path(self.src_path1)
        self.assertEqual((path, marker), (None, None))
        bucket.store_result(self.src_path1, self.result_path1)
        path, marker = bucket.get_source_path(self.src_path1)
        self.assertEqual(marker, '1')
        return

    def test_get_result_path(self):
        bucket = Bucket(self.workdir)
        path = bucket.get_result_path(self.src_path1)
        self.assertEqual(path, None)
        bucket.store_result(self.src_path1, self.result_path1)
        path = bucket.get_result_path(self.src_path1)
        self.assertNotEqual(path, None)
        bucket.store_result(self.src_path1, self.result_path1, suffix='foo')
        path = bucket.get_result_path(self.src_path1, suffix='foo')
        self.assertTrue(path.endswith('result_1__foo'))
        path = bucket.get_result_path(self.src_path1, suffix='bar')
        self.assertEqual(path, None)
        return

    def test_store_result(self):
        bucket = Bucket(self.workdir)
        bucket.store_result(self.src_path1, self.result_path1)
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
        bucket.store_result(self.src_path1, self.result_path1)
        bucket.store_result(self.src_path2, self.result_path2)
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
        bucket.store_result(self.src_path1, self.result_path1, suffix='foo')

        listing = os.listdir(os.path.join(self.workdir, 'results'))
        self.assertEqual(listing, ['result_1__foo'])

        bucket.store_result(self.src_path1, self.result_path1)
        bucket.store_result(self.src_path1, self.result_path2)
        bucket.store_result(self.src_path1, self.result_path1)

        listing = sorted(os.listdir(os.path.join(self.workdir, 'results')))
        self.assertEqual(listing, ['result_1__foo', 'result_1_default'])

        curr_num = bucket.get_current_num()
        self.assertEqual(curr_num, 1)
        return

    def test_store_result_with_suffix(self):
        bucket = Bucket(self.workdir)
        bucket.store_result(self.src_path1, self.result_path1, suffix='foo')
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
        marker = bucket.store_result(
            self.src_path1, self.result_path1, suffix='foo')
        self.assertEqual(marker, '1')
        marker = bucket.store_result(
            self.src_path1, self.result_path2, suffix='foo')
        self.assertEqual(marker, '1')
        marker = bucket.store_result(
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
    #                self.inputdir, 'stressource%s' % x), 'w').write(
    #            str(x) + '\n')
    #    self.assertEqual(len(os.listdir(self.inputdir)), stressnum+4)
    #    for x in xrange(stressnum):
    #        bucket.store_result(
    #            os.path.join(self.inputdir, 'stressource%s' % x),
    #            self.result_path1)
    #    self.assertEqual(bucket.get_current_num(), stressnum)
    #    return

    def test_get_all_source_paths(self):
        bucket = Bucket(self.workdir)
        paths = bucket.get_all_source_paths()
        self.assertTrue(
            isinstance(paths, types.GeneratorType))
        paths = list(paths)
        self.assertEqual(paths, [])
        bucket.store_result(
            self.src_path1, self.result_path1, suffix='foo')
        paths = list(bucket.get_all_source_paths())
        self.assertTrue(paths[0].endswith('source_1'))
        self.assertEqual(len(paths), 1)

        bucket.store_result(
            self.src_path2, self.result_path2, suffix='bar')
        paths = list(bucket.get_all_source_paths())
        self.assertEqual(len(paths), 2)
        return

    def test_get_all_source_paths_ignore_nonsense(self):
        bucket = Bucket(self.workdir)
        open(os.path.join(self.workdir, 'sources', 'source3'),
             'w').write('Hi')
        open(os.path.join(self.workdir, 'sources', 'foo_3'),
             'w').write('Hi')
        paths1 = list(bucket.get_all_source_paths())
        bucket.store_result(
            self.src_path1, self.result_path1, suffix='foo')
        paths2 = list(bucket.get_all_source_paths())
        self.assertEqual(paths1, [])
        self.assertEqual(len(paths2), 1)

    def test_get_result_path_from_marker(self):
        bucket = Bucket(self.workdir)
        marker1 = bucket.store_result(
            self.src_path1, self.result_path1, suffix=None)
        marker2 = bucket.store_result(
            self.src_path1, self.result_path1, suffix='foo')
        marker3 = bucket.store_result(
            self.src_path2, self.result_path1, suffix='foo')
        path1 = bucket.get_result_path_from_marker(marker1)
        path2 = bucket.get_result_path_from_marker(marker2, suffix='foo')
        path3 = bucket.get_result_path_from_marker(marker3, suffix='foo')
        path4 = bucket.get_result_path_from_marker(marker3, suffix='bar')
        path5 = bucket.get_result_path_from_marker('1')
        path6 = bucket.get_result_path_from_marker('3')
        expected_path1 = os.path.join('results', 'result_1_default')
        expected_path2 = os.path.join('results', 'result_1__foo')
        expected_path3 = os.path.join('results', 'result_2__foo')
        self.assertTrue(path1.endswith(expected_path1))
        self.assertTrue(path2.endswith(expected_path2))
        self.assertTrue(path3.endswith(expected_path3))
        self.assertTrue(path4 is None)
        self.assertTrue(path5 is not None)
        self.assertTrue(path6 is None)

    def test_get_marker_from_bucket_file_path(self):
        # We can extract a bucket marker from a result path
        bucket = Bucket(self.workdir)
        marker1 = bucket.store_result(
            self.src_path1, self.result_path1, suffix=None)
        marker2 = bucket.store_result(
            self.src_path1, self.result_path1, suffix='foo')
        path1 = bucket.get_result_path_from_marker(marker1)
        path2 = bucket.get_result_path_from_marker(marker2, suffix='foo')
        path3 = 'misformatted-path'
        result1 = bucket.get_marker_from_bucket_file_path(path1)
        result2 = bucket.get_marker_from_bucket_file_path(path2)
        result3 = bucket.get_marker_from_bucket_file_path(path3)
        self.assertEqual(result1, '1')
        self.assertEqual(result2, '1')
        self.assertEqual(result3, None)


class TestCacheManager(CachingComponentsTestCase):

    def test_markerhandling(self):
        cm = CacheManager(self.workdir)
        marker_string = cm._compose_marker(
            'somefakedhash', 3)
        self.assertEqual(marker_string, 'somefakedhash_3')
        hash, bucket_marker = cm._dissolve_marker('somefakedhash_3')
        self.assertEqual(hash, 'somefakedhash')
        self.assertEqual(bucket_marker, '3')
        self.assertEqual(cm._dissolve_marker('asd'), (None, None))
        self.assertEqual(cm._dissolve_marker(object()), (None, None))
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
        open(broken_cache_dir, 'w').write('i am a file')
        self.assertRaises(IOError, CacheManager, broken_cache_dir)
        return

    def test_compose_marker(self):
        cm = CacheManager(self.workdir)
        marker1 = cm._compose_marker('some_hash_digest', None)
        marker2 = cm._compose_marker('some_hash_digest', 'bucket_marker')
        self.assertEqual(marker1, 'some_hash_digest')
        self.assertEqual(marker2, 'some_hash_digest_bucket_marker')

    def test_get_bucket_path_from_path(self):
        cm = CacheManager(self.workdir)
        path = cm._get_bucket_path_from_path(self.src_path1)
        expected_path_end = os.path.join(
            '73', '737b337e605199de28b3b64c674f9422')
        self.assertEqual(os.listdir(self.workdir), [])
        self.assertTrue(path.endswith(expected_path_end))
        return

    def test_get_bucket_path_from_hash(self):
        cm = CacheManager(self.workdir)
        hash_val = cm.get_hash(self.src_path1)
        path = cm._get_bucket_path_from_hash(hash_val)
        expected_path_end = os.path.join(
            '73', '737b337e605199de28b3b64c674f9422')
        self.assertEqual(os.listdir(self.workdir), [])
        self.assertTrue(path.endswith(expected_path_end))

        path = cm._get_bucket_path_from_hash('nonsense')
        self.assertEqual(path, None)
        return

    def test_prepare_cache_dir(self):
        new_cache_dir = os.path.join(self.workdir, 'newcache')
        broken_cache_dir = os.path.join(self.workdir, 'broken')
        open(broken_cache_dir, 'w').write('broken')
        cm = CacheManager(self.workdir)

        cm.cache_dir = None
        self.assertEqual(cm.prepare_cache_dir(), None)

        cm.cache_dir = new_cache_dir
        cm.prepare_cache_dir()
        self.assertTrue(os.path.isdir(new_cache_dir))

        cm.cache_dir = broken_cache_dir
        self.assertRaises(IOError, cm.prepare_cache_dir)
        return

    def test_get_bucket_from_path(self):
        cache_dir_len1 = len(os.listdir(self.workdir))
        cm = CacheManager(self.workdir)
        bucket1 = cm.get_bucket_from_path(self.src_path1)
        cache_dir_len2 = len(os.listdir(self.workdir))
        self.assertTrue(isinstance(bucket1, Bucket))
        self.assertTrue(cache_dir_len2 == cache_dir_len1 + 1)
        return

    def test_get_cached_file(self):
        cm = CacheManager(self.workdir)
        path = cm.get_cached_file(self.src_path1)
        self.assertTrue(path is None)
        self.assertEqual(os.listdir(self.workdir), [])

        cm.register_doc(self.src_path1, self.result_path1, suffix=None)
        path1 = cm.get_cached_file(self.src_path1)
        path2 = cm.get_cached_file(self.src_path1, suffix='bar')
        path3 = cm.get_cached_file(self.src_path1, suffix='foo')
        self.assertTrue(path1 is not None)
        self.assertTrue(path2 is None)
        self.assertTrue(path3 is None)

        cm.register_doc(self.src_path2, self.result_path1, suffix='foo')
        path1 = cm.get_cached_file(self.src_path2)
        path2 = cm.get_cached_file(self.src_path2, suffix='bar')
        path3 = cm.get_cached_file(self.src_path2, suffix='foo')
        self.assertTrue(path1 is None)
        self.assertTrue(path2 is None)
        self.assertTrue(path3 is not None)
        return

    def test_get_cached_file_from_marker(self):
        cm = CacheManager(self.workdir)
        path1 = cm.get_cached_file_from_marker('not-a-marker')
        path2 = cm.get_cached_file_from_marker(
            '737b337e605199de28b3b64c674f9422_1')
        path3 = cm.get_cached_file_from_marker('not-a-marker-with_underscore')
        marker1 = cm.register_doc(
            self.src_path1, self.result_path1, suffix=None)
        path4 = cm.get_cached_file_from_marker(marker1)

        marker2 = cm.register_doc(
            self.src_path1, self.result_path2, suffix='foo')
        path5 = cm.get_cached_file_from_marker(marker2, suffix='foo')

        self.assertTrue(path1 is None)
        self.assertTrue(path2 is None)
        self.assertTrue(path3 is None)
        self.assertTrue(path4 is not None)
        self.assertTrue(path5 is not None)
        return

    def test_register_doc(self):
        cm = CacheManager(self.workdir)
        marker1 = cm.register_doc(
            self.src_path1, self.result_path1, suffix=None)
        marker2 = cm.register_doc(
            self.src_path1, self.result_path1, suffix=None)
        marker3 = cm.register_doc(
            self.src_path1, self.result_path2, suffix='foo')
        marker4 = cm.register_doc(
            self.src_path2, self.result_path2, suffix='foo')
        self.assertEqual(marker1, '737b337e605199de28b3b64c674f9422_1')
        self.assertEqual(marker2, '737b337e605199de28b3b64c674f9422_1')
        self.assertEqual(marker3, '737b337e605199de28b3b64c674f9422_1')
        self.assertEqual(marker4, 'd5aa51d7fb180729089d2de904f7dffe_1')
        return

    def test_get_hash(self):
        cm = CacheManager(self.workdir)
        hash1 = cm.get_hash(self.src_path1)
        hash2 = cm.get_hash(self.src_path2)
        src = os.path.join(  # a binary stream not convertible to utf-8
            os.path.dirname(__file__), 'input', 'testdoc1.doc')
        hash3 = cm.get_hash(src)
        self.assertEqual(hash1, '737b337e605199de28b3b64c674f9422')
        self.assertEqual(hash2, 'd5aa51d7fb180729089d2de904f7dffe')
        self.assertEqual(hash3, '443a07e0e92b7dc6b21f8be6a388f05f')
        self.assertRaises(TypeError, cm.get_hash)
        return

    def test_contains(self):
        cm = CacheManager(self.workdir)
        self.assertRaises(TypeError, cm.contains)
        self.assertRaises(TypeError, cm.contains, path='foo', marker='bar')
        self.assertFalse(
            cm.contains(marker='737b337e605199de28b3b64c674f9422_1'))

        cm.register_doc(
            self.src_path1, self.result_path1, suffix=None)
        cm.register_doc(
            self.src_path2, self.result_path2, suffix='foo')
        result1 = cm.contains(path=self.src_path1)
        result2 = cm.contains(marker='737b337e605199de28b3b64c674f9422_1')
        result3 = cm.contains(marker='737b337e605199de28b3b64c674f9422_1',
                              suffix='foo')
        result4 = cm.contains(marker='737b337e605199de28b3b64c674f9422_1',
                              suffix='bar')
        result5 = cm.contains(marker='d5aa51d7fb180729089d2de904f7dffe_1',
                              suffix='foo')
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertFalse(result3)
        self.assertFalse(result4)
        self.assertTrue(result5)
        return

    def test_get_all_sources(self):
        cm = CacheManager(self.workdir)
        result1 = cm.get_all_sources()
        self.assertTrue(isinstance(result1, types.GeneratorType))
        self.assertEqual(list(result1), [])

        cm.register_doc(
            self.src_path1, self.result_path1, suffix=None)
        cm.register_doc(
            self.src_path2, self.result_path2, suffix='foo')
        result2 = list(cm.get_all_sources())
        self.assertTrue(len(result2) == 2)

        open(os.path.join(self.workdir, 'crapfile'), 'w').write('crap')
        result3 = list(cm.get_all_sources())
        self.assertFalse('crap' in result3)

        os.mkdir(os.path.join(self.workdir, 'crapdir'))
        result4 = list(cm.get_all_sources())
        self.assertFalse('crapdir' in result4)

        os.makedirs(os.path.join(self.workdir, '66', 'invalid_hashdir'))
        result5 = list(cm.get_all_sources())
        self.assertFalse('66' in result5)
        return

    def test_get_marker_from_path(self):
        cm = CacheManager(self.workdir)
        cm.register_doc(
            self.src_path1, self.result_path1, suffix='foo')
        result = cm.get_marker_from_path(self.src_path1)
        self.assertEqual(result, '737b337e605199de28b3b64c674f9422_1')

    def test_get_marker_from_path_invalid_path(self):
        cm = CacheManager(self.workdir)
        result = cm.get_marker_from_path('not-a-valid-path')
        self.assertEqual(result, None)

    def test_get_marker_from_path_uncached(self):
        cm = CacheManager(self.workdir)
        result = cm.get_marker_from_path(self.src_path1)
        self.assertEqual(result, None)

    def test_get_marker_from_in_cache_path(self):
        cm = CacheManager(self.workdir)
        marker1 = cm.register_doc(
            self.src_path1, self.result_path1, suffix='foo')
        marker2 = cm.register_doc(
            self.src_path2, self.result_path2, suffix=None)
        result_path1 = cm.get_cached_file_from_marker(marker1, suffix='foo')
        result_path2 = cm.get_cached_file_from_marker(marker2, suffix=None)
        src_path = sorted(list(cm.get_all_sources()))[0]
        result1 = cm.get_marker_from_in_cache_path(result_path1)
        result2 = cm.get_marker_from_in_cache_path(result_path2)
        result3 = cm.get_marker_from_in_cache_path(src_path)
        self.assertEqual(result1, '737b337e605199de28b3b64c674f9422_1')
        self.assertEqual(result2, 'd5aa51d7fb180729089d2de904f7dffe_1')
        self.assertEqual(result3, '737b337e605199de28b3b64c674f9422_1')

    def test_get_marker_from_in_cache_path_no_path(self):
        cm = CacheManager(self.workdir)
        result = cm.get_marker_from_in_cache_path(None)
        self.assertEqual(result, None)

    def test_get_marker_from_in_cache_path_invalid_path(self):
        cm = CacheManager(self.workdir)
        result = cm.get_marker_from_in_cache_path('not-a-valid-path')
        self.assertEqual(result, None)

    def test_get_hash_from_incache_path(self):
        cm = CacheManager(self.workdir, level=2)
        path1 = '/nonsense/not-in-cache'
        path2 = os.path.join(self.workdir, 'Nonsense')
        path3 = os.path.join(self.workdir, 'foo', 'bar')
        path4 = os.path.join(self.workdir, 'foo', 'bar', 'baz')
        path5 = os.path.join(self.workdir, 'foo', 'bar', 'baz', 'boo')
        path6 = os.path.join(self.workdir,
                             'foo', 'bar', 'baz', 'boo', 'result_1__foo')
        self.assertTrue(cm._get_hash_from_in_cache_path(None) is None)
        self.assertTrue(cm._get_hash_from_in_cache_path(path1) is None)
        self.assertTrue(cm._get_hash_from_in_cache_path(path2) is None)
        self.assertTrue(cm._get_hash_from_in_cache_path(path3) is None)
        self.assertEqual(cm._get_hash_from_in_cache_path(path4), 'baz')
        self.assertEqual(cm._get_hash_from_in_cache_path(path5), 'baz')
        self.assertEqual(cm._get_hash_from_in_cache_path(path6), 'baz')

    def test_get_hash_from_incache_path_source_paths(self):
        # Make sure we also get markers from source file paths
        cm = CacheManager(self.workdir, level=2)
        cm.register_doc(
            self.src_path1, self.result_path1, suffix='foo')
        cm.register_doc(
            self.src_path2, self.result_path2, suffix=None)
        src_path1, src_path2 = cm.get_all_sources()
        self.assertEqual(
            cm._get_hash_from_in_cache_path(src_path1),
            '737b337e605199de28b3b64c674f9422')
        self.assertEqual(
            cm._get_hash_from_in_cache_path(src_path2),
            'd5aa51d7fb180729089d2de904f7dffe')


class NotHashingCacheManager(CacheManager):
    # a cache manager that always returns the same hash
    def get_hash(self, path=None):
        return 'somefakedhash'


class TestCollision(CachingComponentsTestCase):
    # make sure hash collisions are handled correctly

    def test_collisions(self):
        cm = NotHashingCacheManager(cache_dir=self.workdir)
        cm.register_doc(source_path=self.src_path1,
                        to_cache=self.result_path1, suffix='pdf')
        cm.register_doc(source_path=self.src_path1,
                        to_cache=self.result_path2, suffix='html')
        cm.register_doc(source_path=self.src_path2,
                        to_cache=self.result_path3, suffix='pdf')
        cm.register_doc(source_path=self.src_path2,
                        to_cache=self.result_path4, suffix='html')
        basket_path = os.path.join(self.workdir, 'so', 'somefakedhash')
        self.assertEqual(
            ['source_1', 'source_2'],
            sorted(os.listdir(os.path.join(basket_path, 'sources'))))
        self.assertEqual(
            ['result_1__html', 'result_1__pdf',
             'result_2__html', 'result_2__pdf'
              ],
            sorted(os.listdir(os.path.join(basket_path, 'results'))))

        result_path = os.path.join(basket_path, 'results', 'result_1__pdf')
        self.assertEqual('result1\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, 'results', 'result_1__html')
        self.assertEqual('result2\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, 'results', 'result_2__pdf')
        self.assertEqual('result3\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, 'results', 'result_2__html')
        self.assertEqual('result4\n', open(result_path, 'r').read())
        pass
