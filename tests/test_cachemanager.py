import filecmp
import os
import shutil
import tempfile
import unittest
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from ulif.openoffice.cachemanager import Bucket, CacheManager, get_marker


class HelpersTestCase(unittest.TestCase):

    def test_get_marker(self):
        # Make sure, sorted dicts get the same marker
        result1 = get_marker()
        result2 = get_marker(options={})
        result3 = get_marker(options={'b': '0', 'a': '1'})
        result4 = get_marker(options={'a': '1', 'b': '0'})
        assert result1 == 'W10'
        assert result2 == 'W10'
        assert result3 == result4
        assert result2 != result3


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
        for subdirname in ['sources', 'repr', 'keys', 'data']:
            self.assertTrue(
                os.path.exists(os.path.join(self.workdir, subdirname)),
                'Not found: subdir/file `%s`' % subdirname
                )

        # Main attributes are set properly...
        self.assertEqual(
            bucket.srcdir, os.path.join(self.workdir, 'sources'))
        self.assertEqual(
            bucket.resultdir, os.path.join(self.workdir, 'repr'))
        self.assertEqual(
            bucket.keysdir, os.path.join(self.workdir, 'keys'))
        self.assertEqual(
            bucket._data, dict(version=1, curr_src_num=0,
                               curr_repr_num=dict()))

        # A bucket with same path won't overwrite existing data...
        data = bucket._get_internal_data()
        self.assertEqual(
            data, dict(version=1, curr_src_num=0, curr_repr_num=dict()))
        bucket._set_internal_data(
            dict(version=1, curr_src_num=1, curr_repr_num={'1': 2}))
        bucket2 = Bucket(self.workdir)
        data = bucket2._get_internal_data()
        self.assertEqual(data['curr_src_num'], 1)
        self.assertEqual(data['curr_repr_num']['1'], 2)
        return

    def test_curr_src_num(self):
        # we can get/set current source number
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.get_current_source_num(), 0)
        bucket.set_current_source_num(12)
        self.assertEqual(bucket.get_current_source_num(), 12)
        return

    def test_curr_repr_num(self):
        # we can get/set current representation number
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.get_current_repr_num(1), 0)
        self.assertEqual(bucket.get_current_repr_num('2'), 0)
        bucket.set_current_repr_num('1', 12)
        self.assertEqual(bucket.get_current_repr_num('1'), 12)
        self.assertEqual(bucket.get_current_repr_num('2'), 0)
        return

    def test_get_stored_source_num(self):
        # we can test whether a source file is stored in a bucket already.
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.get_stored_source_num(self.src_path1), None)
        self.assertEqual(bucket.get_stored_source_num(self.src_path2), None)
        shutil.copyfile(
            self.src_path1, os.path.join(bucket.srcdir, 'source_1'))
        self.assertEqual(bucket.get_stored_source_num(self.src_path1), 1)
        self.assertEqual(bucket.get_stored_source_num(self.src_path2), None)
        shutil.copyfile(
            self.src_path2, os.path.join(bucket.srcdir, 'source_2'))
        self.assertEqual(bucket.get_stored_source_num(self.src_path1), 1)
        self.assertEqual(bucket.get_stored_source_num(self.src_path2), 2)
        return

    def test_get_stored_repr_num(self):
        # we can get a representation number if the repective key is
        # stored in the bucket already.
        bucket = Bucket(self.workdir)
        key_path1 = os.path.join(bucket.keysdir, '1', '1.key')
        key_path2 = os.path.join(bucket.keysdir, '1', '2.key')
        key_path3 = os.path.join(bucket.keysdir, '2', '1.key')
        self.assertEqual(bucket.get_stored_repr_num(1, 'somekey'), None)
        self.assertEqual(bucket.get_stored_repr_num(1, 'otherkey'), None)
        self.assertEqual(bucket.get_stored_repr_num(2, 'somekey'), None)
        self.assertEqual(bucket.get_stored_repr_num(2, 'otherkey'), None)
        os.makedirs(os.path.dirname(key_path1))
        os.makedirs(os.path.dirname(key_path3))
        open(key_path1, 'w').write(b'otherkey')
        self.assertEqual(bucket.get_stored_repr_num(1, 'somekey'), None)
        self.assertEqual(bucket.get_stored_repr_num(1, 'otherkey'), 1)
        self.assertEqual(bucket.get_stored_repr_num(2, 'somekey'), None)
        self.assertEqual(bucket.get_stored_repr_num(2, 'otherkey'), None)
        open(key_path2, 'w').write(b'somekey')
        self.assertEqual(bucket.get_stored_repr_num(1, 'somekey'), 2)
        self.assertEqual(bucket.get_stored_repr_num(1, 'otherkey'), 1)
        self.assertEqual(bucket.get_stored_repr_num(2, 'somekey'), None)
        self.assertEqual(bucket.get_stored_repr_num(2, 'otherkey'), None)
        open(key_path3, 'w').write(b'somekey')
        self.assertEqual(bucket.get_stored_repr_num(1, 'somekey'), 2)
        self.assertEqual(bucket.get_stored_repr_num(1, 'otherkey'), 1)
        self.assertEqual(bucket.get_stored_repr_num(2, 'somekey'), 1)
        self.assertEqual(bucket.get_stored_repr_num(2, 'otherkey'), None)
        return

    def test_store_representation_no_key(self):
        # we can store sources with their representations
        bucket = Bucket(self.workdir)
        res = bucket.store_representation(self.src_path1, self.result_path1)
        exp_stored_src = os.path.join(self.workdir, b'sources', b'source_1')
        exp_stored_repr_dir = os.path.join(self.workdir, b'repr', b'1', b'1')
        exp_stored_repr_data = os.path.join(
            exp_stored_repr_dir, b'resultfile1')
        exp_stored_key = os.path.join(self.workdir, b'keys', b'1', b'1.key')
        self.assertTrue(os.path.isfile(exp_stored_src))
        self.assertTrue(os.path.isdir(exp_stored_repr_dir))
        self.assertTrue(os.path.isfile(exp_stored_repr_data))
        self.assertTrue(os.path.isfile(exp_stored_key))
        self.assertEqual(
            open(exp_stored_src, 'rb').read(), b'source1\n')
        self.assertEqual(
            open(exp_stored_repr_data, 'rb').read(), b'result1\n')
        self.assertEqual(
            open(exp_stored_key, 'rb').read(), b'')
        self.assertEqual(res, '1_1')
        return

    def test_store_representation_string_key(self):
        #  we can store sources with their representations and a string key
        bucket = Bucket(self.workdir)
        res = bucket.store_representation(
            self.src_path1, self.result_path1, repr_key='somekey')
        exp_stored_key = os.path.join(self.workdir, b'keys', b'1', b'1.key')
        self.assertEqual(
            open(exp_stored_key, 'rb').read(), b'somekey')
        self.assertEqual(res, '1_1')
        return

    def test_store_representation_file_key(self):
        #  we can store sources with their representations and a key
        #  stored in a file.
        bucket = Bucket(self.workdir)
        res = bucket.store_representation(
            self.src_path1, self.result_path1, repr_key=StringIO('somekey'))
        exp_stored_key = os.path.join(self.workdir, b'keys', b'1', b'1.key')
        self.assertEqual(
            open(exp_stored_key, 'rb').read(), b'somekey')
        self.assertEqual(res, '1_1')
        return

    def test_store_representation_update_result(self):
        # if we send a different representation for the same source
        # and key, the old representation will be replaced.
        bucket = Bucket(self.workdir)
        res1 = bucket.store_representation(
            self.src_path1, self.result_path1, repr_key='mykey')
        res2 = bucket.store_representation(
            self.src_path1, self.result_path2, repr_key='mykey')
        exp_stored_repr_dir = os.path.join(self.workdir, b'repr', b'1', b'1')
        old_stored_repr_data = os.path.join(
            exp_stored_repr_dir, b'resultfile1')
        exp_stored_repr_data = os.path.join(
            exp_stored_repr_dir, b'resultfile2')
        self.assertEqual(res1, b'1_1')
        self.assertEqual(res2, b'1_1')
        self.assertEqual(
            open(exp_stored_repr_data, 'rb').read(), 'result2\n')
        self.assertEqual(
            os.path.exists(old_stored_repr_data), False)
        return

    def test_get_representation_unstored(self):
        # we cannot get unstored representations
        bucket = Bucket(self.workdir)
        self.assertEqual(bucket.get_representation(b'1_1'), None)
        return

    def test_get_representation_stored(self):
        # we cannot get unstored representations
        bucket = Bucket(self.workdir)
        res1 = bucket.store_representation(
            self.src_path1, self.result_path1, repr_key=b'mykey')
        exp_repr_path = os.path.join(
            self.workdir, b'repr', b'1', b'1', b'resultfile1')
        res2 = bucket.get_representation(res1)
        self.assertEqual(res1, b'1_1')
        self.assertEqual(res2, exp_repr_path)
        return

    def test_keys(self):
        # we can get a list of all bucket keys in a bucket.
        bucket = Bucket(self.workdir)
        self.assertEqual(list(bucket.keys()), [])
        b_key1 = bucket.store_representation(
            self.src_path1, self.result_path1, repr_key=b'foo')
        self.assertEqual(list(bucket.keys()), [b_key1])
        b_key2 = bucket.store_representation(
            self.src_path1, self.result_path2, repr_key=b'bar')
        self.assertEqual(
            sorted(list(bucket.keys())), sorted([b_key1, b_key2]))
        b_key3 = bucket.store_representation(
            self.src_path2, self.result_path1, repr_key=b'baz')
        self.assertEqual(
            sorted(list(bucket.keys())), sorted([b_key1, b_key2, b_key3]))
        return


class TestCacheManager(CachingComponentsTestCase):

    def test_markerhandling(self):
        cm = CacheManager(self.workdir)
        marker_string = cm._compose_cache_key(
            'somefakedhash', 3)
        self.assertEqual(marker_string, 'somefakedhash_3')
        hash, bucket_marker = cm._dissolve_cache_key('somefakedhash_3')
        self.assertEqual(hash, 'somefakedhash')
        self.assertEqual(bucket_marker, '3')
        self.assertEqual(cm._dissolve_cache_key('asd'), (None, None))
        self.assertEqual(cm._dissolve_cache_key(object()), (None, None))
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
        marker2 = cm._compose_cache_key('some_hash_digest', 'bucket_marker')
        self.assertEqual(marker2, 'some_hash_digest_bucket_marker')

    def test_get_bucket_path(self):
        cm = CacheManager(self.workdir)
        hash_val = cm.get_hash(self.src_path1)
        path = cm._get_bucket_path(hash_val)
        expected_path_end = os.path.join(
            '73', '737b337e605199de28b3b64c674f9422')
        self.assertEqual(os.listdir(self.workdir), [])
        self.assertTrue(path.endswith(expected_path_end))
        return

    def test_prepare_cache_dir(self):
        new_cache_dir = os.path.join(self.workdir, 'newcache')
        broken_cache_dir = os.path.join(self.workdir, 'broken')
        open(broken_cache_dir, 'w').write('broken')
        cm = CacheManager(self.workdir)

        cm.cache_dir = None
        self.assertEqual(cm._prepare_cache_dir(), None)

        cm.cache_dir = new_cache_dir
        cm._prepare_cache_dir()
        self.assertTrue(os.path.isdir(new_cache_dir))

        cm.cache_dir = broken_cache_dir
        self.assertRaises(IOError, cm._prepare_cache_dir)
        return

    def test_get_cached_file(self):
        cm = CacheManager(self.workdir)
        path = cm.get_cached_file(self.src_path1)
        self.assertTrue(path is None)
        self.assertEqual(os.listdir(self.workdir), [])

        my_id1 = cm.register_doc(self.src_path1, self.result_path1)
        path1 = cm.get_cached_file(my_id1)
        self.assertTrue(path1 is not None)

        my_id2 = cm.register_doc(
            self.src_path2, self.result_path1, repr_key='foo')
        path1 = cm.get_cached_file(my_id2)
        self.assertTrue(path1 is not None)

        my_id3 = cm.register_doc(
            self.src_path2, self.result_path1, repr_key=StringIO('foo'))
        path1 = cm.get_cached_file(my_id3)
        self.assertTrue(path1 is not None)
        self.assertEqual(my_id2, my_id3)

        self.assertEqual(cm.get_cached_file('nonsense_really'), None)
        return

    def test_get_cached_file_by_src(self):
        # we can get a cached file by source file and options
        cm = CacheManager(self.workdir)
        # without a cache key
        my_id1 = cm.register_doc(self.src_path1, self.result_path1)
        result1 = cm.get_cached_file_by_source(self.src_path1)
        assert filecmp.cmp(result1, self.result_path1, shallow=False)

    def test_get_cached_file_by_src_failed(self):
        cm = CacheManager(self.workdir)
        result1 = cm.get_cached_file_by_source(self.src_path1)
        assert result1 is None

    def test_get_cached_file_by_src_w_key(self):
        cm = CacheManager(self.workdir)
        my_id = cm.register_doc(self.src_path1, self.result_path1, 'mykey')
        result1 = cm.get_cached_file_by_source(self.src_path1, 'mykey')
        assert filecmp.cmp(result1, self.result_path1, shallow=False)
        result2 = cm.get_cached_file_by_source(self.src_path1, 'otherkey')
        assert result2 is None
        cm.register_doc(self.src_path1, self.result_path2, 'otherkey')
        result3 = cm.get_cached_file_by_source(self.src_path1, 'otherkey')
        assert filecmp.cmp(result3, self.result_path2, shallow=False)

    def test_register_doc(self):
        cm = CacheManager(self.workdir)
        marker1 = cm.register_doc(
            self.src_path1, self.result_path1)
        marker2 = cm.register_doc(
            self.src_path1, self.result_path1)
        marker3 = cm.register_doc(
            self.src_path1, self.result_path2, repr_key=b'foo')
        marker4 = cm.register_doc(
            self.src_path2, self.result_path2, repr_key=b'foo')
        marker5 = cm.register_doc(
            self.src_path2, self.result_path2, repr_key=StringIO(b'bar'))
        self.assertEqual(marker1, b'737b337e605199de28b3b64c674f9422_1_1')
        self.assertEqual(marker2, b'737b337e605199de28b3b64c674f9422_1_1')
        self.assertEqual(marker3, b'737b337e605199de28b3b64c674f9422_1_2')
        self.assertEqual(marker4, b'd5aa51d7fb180729089d2de904f7dffe_1_1')
        self.assertEqual(marker5, b'd5aa51d7fb180729089d2de904f7dffe_1_2')
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

    def test_keys(self):
        # we can get all cache keys
        cm = CacheManager(self.workdir)
        key1 = cm.register_doc(self.src_path1, self.result_path1, 'foo')
        self.assertEqual(
            list(cm.keys()),
            ['737b337e605199de28b3b64c674f9422_1_1']
            )
        key2 = cm.register_doc(self.src_path1, self.result_path2, 'bar')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             ]
            )
        key3 = cm.register_doc(self.src_path2, self.result_path1, 'baz')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             'd5aa51d7fb180729089d2de904f7dffe_1_1',
             ]
            )
        return

    def test_keys_custom_level(self):
        # we can get all cache keys also with custom level set
        cm = CacheManager(self.workdir, level=3)
        key1 = cm.register_doc(self.src_path1, self.result_path1, 'foo')
        self.assertEqual(
            list(cm.keys()),
            ['737b337e605199de28b3b64c674f9422_1_1']
            )
        key2 = cm.register_doc(self.src_path1, self.result_path2, 'bar')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             ]
            )
        key3 = cm.register_doc(self.src_path2, self.result_path1, 'baz')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             'd5aa51d7fb180729089d2de904f7dffe_1_1',
             ]
            )
        return


class NotHashingCacheManager(CacheManager):
    # a cache manager that always returns the same hash
    def get_hash(self, path=None):
        return 'somefakedhash'


class TestCollision(CachingComponentsTestCase):
    # make sure hash collisions are handled correctly

    def test_collisions(self):
        cm = NotHashingCacheManager(cache_dir=self.workdir)
        cm.register_doc(source_path=self.src_path1,
                        to_cache=self.result_path1, repr_key='pdf')
        cm.register_doc(source_path=self.src_path1,
                        to_cache=self.result_path2, repr_key='html')
        cm.register_doc(source_path=self.src_path2,
                        to_cache=self.result_path3, repr_key='pdf')
        cm.register_doc(source_path=self.src_path2,
                        to_cache=self.result_path4, repr_key='html')
        basket_path = os.path.join(self.workdir, 'so', 'somefakedhash')
        self.assertEqual(
            ['source_1', 'source_2'],
            sorted(os.listdir(os.path.join(basket_path, 'sources'))))
        self.assertEqual(
            ['1', '2'],
            sorted(os.listdir(os.path.join(basket_path, 'repr'))))

        self.assertEqual(
            ['1', '2'],
            sorted(os.listdir(os.path.join(basket_path, 'repr', '1'))))
        self.assertEqual(
            ['1', '2'],
            sorted(os.listdir(os.path.join(basket_path, 'repr', '2'))))

        self.assertEqual(
            ['resultfile1'],
            sorted(os.listdir(os.path.join(basket_path, 'repr', '1', '1'))))
        self.assertEqual(
            ['resultfile2'],
            sorted(os.listdir(os.path.join(basket_path, 'repr', '1', '2'))))

        file_list = []
        for root, dirnames, filenames in os.walk(
            os.path.join(basket_path, 'repr')):
            for filename in filenames:
                file_list.append(os.path.join(root, filename))
        file_list = sorted(file_list)
        sfile_list = [x[len(basket_path) + 1:] for x in file_list]
        self.assertEqual(
            sfile_list,
            ['repr/1/1/resultfile1', 'repr/1/2/resultfile2',
             'repr/2/1/resultfile3', 'repr/2/2/resultfile4']
            )

        result_path = os.path.join(basket_path, sfile_list[0])
        self.assertEqual('result1\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, sfile_list[1])
        self.assertEqual('result2\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, sfile_list[2])
        self.assertEqual('result3\n', open(result_path, 'r').read())

        result_path = os.path.join(basket_path, sfile_list[3])
        self.assertEqual('result4\n', open(result_path, 'r').read())
        pass
