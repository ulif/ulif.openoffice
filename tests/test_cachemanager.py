import filecmp
import os
import pytest
import shutil
import tempfile
import unittest
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from ulif.openoffice.cachemanager import Bucket, CacheManager, get_marker


def write_to_file(path, content):
    with open(path, 'w') as fd:
        fd.write(content)


class TestHelpers(object):

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


@pytest.fixture(scope="function")
def cache_env(request, tmpdir):
    (tmpdir / "work" / "src1.txt").write("source1\n", ensure=True)
    (tmpdir / "work" / "src2.txt").write("source2\n")
    (tmpdir / "work" / "result1.txt").write("result1\n")
    (tmpdir / "work" / "result2.txt").write("result2\n")
    (tmpdir / "work" / "result3.txt").write("result3\n")
    (tmpdir / "work" / "result4.txt").write("result4\n")
    return tmpdir


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
        write_to_file(self.src_path1, 'source1\n')
        write_to_file(self.src_path2, 'source2\n')
        write_to_file(self.result_path1, 'result1\n')
        write_to_file(self.result_path2, 'result2\n')
        write_to_file(self.result_path3, 'result3\n')
        write_to_file(self.result_path4, 'result4\n')

    def tearDown(self):
        shutil.rmtree(self.workdir)
        shutil.rmtree(self.inputdir)


class TestCacheBucke(object):
    # Tests for CacheBucket

    def test_init_creates_subdirs(self, tmpdir):
        # a new bucket contains certain subdirs and a file
        Bucket(str(tmpdir))
        for filename in ['sources', 'repr', 'keys', 'data']:
            assert tmpdir.join(filename).exists()

    def test_init_sets_attributes(self, tmpdir):
        # Main attributes are set properly...
        bucket = Bucket(str(tmpdir))
        assert bucket.srcdir == tmpdir / "sources"
        assert bucket.resultdir == tmpdir / "repr"
        assert bucket.keysdir == tmpdir / "keys"
        assert bucket._data == dict(
            version=1, curr_src_num=0, curr_repr_num=dict())

    def test_init_internal_data(self, tmpdir):
        # A bucket with same path won't overwrite existing data...
        bucket1 = Bucket(str(tmpdir))
        assert bucket1._get_internal_data() == dict(
            version=1, curr_src_num=0, curr_repr_num={})
        to_set = dict(version=1, curr_src_num=1, curr_repr_num={'1': 2})
        bucket1._set_internal_data(to_set)
        assert bucket1._get_internal_data() == to_set
        bucket2 = Bucket(str(tmpdir))
        assert bucket2._get_internal_data() == to_set

    def test_curr_src_num(self, tmpdir):
        # we can get/set current source number
        bucket = Bucket(str(tmpdir))
        assert bucket.get_current_source_num() == 0
        bucket.set_current_source_num(12)
        assert bucket.get_current_source_num() == 12

    def test_curr_repr_num(self, tmpdir):
        # we can get/set current representation number
        bucket = Bucket(str(tmpdir))
        assert bucket.get_current_repr_num(1) == 0
        assert bucket.get_current_repr_num('2') == 0
        bucket.set_current_repr_num('1', 12)
        assert bucket.get_current_repr_num('1') == 12
        assert bucket.get_current_repr_num('2') == 0

    def test_get_stored_source_num(self, cache_env):
        # we can test whether a source file is stored in a bucket already.
        bucket = Bucket(str(cache_env.join("cache")))
        src1 = cache_env / "work" / "src1.txt"
        src2 = cache_env / "work" / "src2.txt"
        assert bucket.get_stored_source_num(str(src1)) is None
        assert bucket.get_stored_source_num(str(src2)) is None
        shutil.copyfile(str(src1), os.path.join(bucket.srcdir, "source_1"))
        assert bucket.get_stored_source_num(str(src1)) == 1
        assert bucket.get_stored_source_num(str(src2)) is None
        shutil.copyfile(str(src2), os.path.join(bucket.srcdir, "source_2"))
        assert bucket.get_stored_source_num(str(src1)) == 1
        assert bucket.get_stored_source_num(str(src2)) == 2

    def test_get_stored_repr_num(self, tmpdir):
        # we can get a representation number if the repective key is
        # stored in the bucket already.
        bucket = Bucket(str(tmpdir.join("cache")))
        key_path1 = tmpdir / "cache" / "keys" / "1" / "1.key"
        key_path2 = tmpdir / "cache" / "keys" / "1" / "2.key"
        key_path3 = tmpdir / "cache" / "keys" / "2" / "1.key"
        assert bucket.get_stored_repr_num(1, 'somekey') is None
        assert bucket.get_stored_repr_num(1, 'otherkey') is None
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path1.write('otherkey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') is None
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path2.write('somekey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') == 2
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path3.write('somekey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') == 2
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') == 1
        assert bucket.get_stored_repr_num(2, 'otherkey') is None

    def test_store_representation_no_key(self, cache_env):
        # we can store sources with their representations
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"))
        source_path = cache_env / "cache" / "sources" / "source_1"
        result_path = cache_env / "cache" / "repr" / "1" / "1" / "result1.txt"
        assert res == "1_1"
        assert source_path.isfile()
        assert source_path.read() == "source1\n"
        assert result_path.dirpath().isdir()
        assert result_path.isfile()
        assert result_path.read() == "result1\n"
        assert (cache_env / "cache" / "keys" / "1" / "1.key").isfile()
        assert (cache_env / "cache" / "keys" / "1" / "1.key").read() == ""

    def test_store_representation_string_key(self, cache_env):
        #  we can store sources with their representations and a string key
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"), repr_key="somekey")
        assert res == "1_1"
        assert (
            cache_env / "cache" / "keys" / "1" / "1.key").read() == 'somekey'

    def test_store_representation_file_key(self, cache_env):
        #  we can store sources with their representations and a key
        #  stored in a file.
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"),
            repr_key=StringIO("somekey"))
        assert res == "1_1"
        assert (
            cache_env / "cache" / "keys" / "1" / "1.key").read() == 'somekey'

    def test_store_representation_update_result(self, cache_env):
        # if we send a different representation for the same source
        # and key, the old representation will be replaced.
        bucket = Bucket(str(cache_env / "cache"))
        res1 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"), repr_key='mykey')
        res2 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result2.txt"), repr_key='mykey')
        assert res1 == "1_1"
        assert res2 == "1_1"
        result_dir = cache_env / "cache" / "repr" / "1" / "1"
        assert result_dir.join("result1.txt").exists() is False
        assert result_dir.join("result2.txt").exists() is True
        assert result_dir.join("result2.txt").read() == "result2\n"

    def test_get_representation_unstored(self, tmpdir):
        # we cannot get unstored representations
        bucket = Bucket(str(tmpdir.join("cache")))
        assert bucket.get_representation("1_1") is None

    def test_get_representation_stored(self, cache_env):
        # we can get paths of representations
        bucket = Bucket(str(cache_env.join("cache")))
        res1 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"), repr_key=b'mykey')
        res2 = bucket.get_representation(res1)
        assert res1 == "1_1"
        assert res2 == cache_env / "cache" / "repr" / "1" / "1" / "result1.txt"

    def test_keys(self, cache_env):
        # we can get a list of all bucket keys in a bucket.
        bucket = Bucket(str(cache_env))
        assert list(bucket.keys()) == []
        key1 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result1.txt"), repr_key='foo')
        assert list(bucket.keys()) == [key1, ]
        key2 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result2.txt"), repr_key='bar')
        assert sorted(list(bucket.keys())) == [key1, key2]
        key3 = bucket.store_representation(
            str(cache_env / "work" / "src1.txt"),
            str(cache_env / "work" / "result3.txt"), repr_key='baz')
        assert sorted(list(bucket.keys())) == [key1, key2, key3]


class TestCacheManagerNew(object):
    # Tests for class `CacheManager`

    def test_markerhandling(self, tmpdir):
        # we can dissolve markers from cache_keys.
        cm = CacheManager(str(tmpdir))
        marker_string =  cm._compose_cache_key('somefakedhash', 3)
        assert marker_string == "somefakedhash_3"
        hash_val, bucket_marker = cm._dissolve_cache_key("somefakedhash_3")
        assert hash_val == "somefakedhash"
        assert bucket_marker == "3"
        assert cm._dissolve_cache_key("asd") == (None, None)
        assert cm._dissolve_cache_key(None) == (None, None)

    def test_init(self, tmpdir):
        # we can initialize a cache manager with default depth
        cm = CacheManager(str(tmpdir.join("cache")))
        assert cm.level == 1
        assert cm.cache_dir == tmpdir.join("cache")

    def test_init_level(self, tmpdir):
        # we can set a level (depth) when creating cache managers
        cm = CacheManager(str(tmpdir.join("cache")))
        assert cm.level == 3

    def test_dir_created(self, tmpdir):
        # a cache dir is created if neccessary
        cache_dir = tmpdir / "cache"
        assert cache_dir.exists() is False
        cm = CacheManager(str(cache_dir))
        assert cache_dir.isdir() is True


class TestCacheManager(CachingComponentsTestCase):

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
        result, key = cm.get_cached_file_by_source(self.src_path1)
        assert filecmp.cmp(result, self.result_path1, shallow=False)
        assert key == '737b337e605199de28b3b64c674f9422_1_1'
        assert my_id1 == key

    def test_get_cached_file_by_src_failed(self):
        cm = CacheManager(self.workdir)
        result, key = cm.get_cached_file_by_source(self.src_path1)
        assert result is None
        assert key is None

    def test_get_cached_file_by_src_w_key(self):
        cm = CacheManager(self.workdir)
        my_id = cm.register_doc(self.src_path1, self.result_path1, 'mykey')
        result1, key1 = cm.get_cached_file_by_source(self.src_path1, 'mykey')
        assert filecmp.cmp(result1, self.result_path1, shallow=False)
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        assert key1 == my_id
        result2, key2 = cm.get_cached_file_by_source(
            self.src_path1, 'otherkey')
        assert result2 is None
        assert key2 is None
        cm.register_doc(self.src_path1, self.result_path2, 'otherkey')
        result3, key3 = cm.get_cached_file_by_source(
            self.src_path1, 'otherkey')
        assert filecmp.cmp(result3, self.result_path2, shallow=False)
        assert key3 == '737b337e605199de28b3b64c674f9422_1_2'

    def test_register_doc(self):
        cm = CacheManager(self.workdir)
        marker1 = cm.register_doc(
            self.src_path1, self.result_path1)
        marker2 = cm.register_doc(
            self.src_path1, self.result_path1)
        marker3 = cm.register_doc(
            self.src_path1, self.result_path2, repr_key='foo')
        marker4 = cm.register_doc(
            self.src_path2, self.result_path2, repr_key='foo')
        marker5 = cm.register_doc(
            self.src_path2, self.result_path2, repr_key=StringIO('bar'))
        self.assertEqual(marker1, '737b337e605199de28b3b64c674f9422_1_1')
        self.assertEqual(marker2, '737b337e605199de28b3b64c674f9422_1_1')
        self.assertEqual(marker3, '737b337e605199de28b3b64c674f9422_1_2')
        self.assertEqual(marker4, 'd5aa51d7fb180729089d2de904f7dffe_1_1')
        self.assertEqual(marker5, 'd5aa51d7fb180729089d2de904f7dffe_1_2')
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
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        key2 = cm.register_doc(self.src_path1, self.result_path2, 'bar')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             ]
            )
        assert key2 == '737b337e605199de28b3b64c674f9422_1_2'
        key3 = cm.register_doc(self.src_path2, self.result_path1, 'baz')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             'd5aa51d7fb180729089d2de904f7dffe_1_1',
             ]
            )
        assert key3 == 'd5aa51d7fb180729089d2de904f7dffe_1_1'
        return

    def test_keys_custom_level(self):
        # we can get all cache keys also with custom level set
        cm = CacheManager(self.workdir, level=3)
        key1 = cm.register_doc(self.src_path1, self.result_path1, 'foo')
        self.assertEqual(
            list(cm.keys()),
            ['737b337e605199de28b3b64c674f9422_1_1']
            )
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        key2 = cm.register_doc(self.src_path1, self.result_path2, 'bar')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             ]
            )
        assert key2 == '737b337e605199de28b3b64c674f9422_1_2'
        key3 = cm.register_doc(self.src_path2, self.result_path1, 'baz')
        self.assertEqual(
            sorted(list(cm.keys())),
            ['737b337e605199de28b3b64c674f9422_1_1',
             '737b337e605199de28b3b64c674f9422_1_2',
             'd5aa51d7fb180729089d2de904f7dffe_1_1',
             ]
            )
        assert key3 == 'd5aa51d7fb180729089d2de904f7dffe_1_1'
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
