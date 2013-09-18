import filecmp
import glob
import os
import shutil
try:
    import cPickle as pickle  # Python 2.x
except ImportError:           # pragma: no cover
    import pickle             # Python 3.x
from hashlib import md5
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from ulif.openoffice.helpers import (
    filelike_cmp, write_filelike, base64url_encode)


def get_marker(options=dict()):
    """Compute a unique marker for a set of options.

    The returned marker is a string suitable for use in
    filessystems. Different sets of options will result in different
    markers where order of options does not matter.

    In :mod:`ulif.openoffice` we use the marker to feed the cache
    manager and to mark different results for the same input file as
    different option sets will result in different output for same
    input.
    """
    result = sorted(options.items())
    result = '%s' % result
    return base64url_encode(result).replace('=', '')


class Bucket(object):
    """A bucket where we store files with same hash sums.

    .. warning:: :class:`Bucket` is not thread-safe!

    A bucket is a directory in filesystem, where you can store triples

      ``(source_file, representation_file, key)``

    where `key` must be a unique identifier for a certain
    `representation`. Each representation (and hence key) belongs to
    one `source_file`, while each `source_file` can be the base for
    multiple representations and their respective keys.

    Keys can be very big, therefore we allow to pass them in as
    strings (byte streams) or as file-like objects.

    The main methods to feed a bucket or retrieve stored data are
    :meth:`store_representation` and :meth:`get_representation`.

    For stored documents you will get a `bucket key` which can be used
    later to retrieve data stored.
    """
    def __init__(self, path):
        self.path = path
        self.srcdir = os.path.join(self.path, 'sources')
        self.resultdir = os.path.join(self.path, 'repr')
        self.keysdir = os.path.join(self.path, 'keys')
        self.create()
        if self.data is None:
            self.data = dict(
                version=1,
                curr_src_num=0,
                curr_repr_num=dict(),
                )
        self._data = self.data

    def _set_internal_data(self, data):
        data_path = os.path.join(self.path, 'data')
        pickle.dump(data, open(data_path, 'wb'))
        return

    def _get_internal_data(self):
        data_path = os.path.join(self.path, 'data')
        if not os.path.exists(data_path):
            return None
        return pickle.load(open(data_path, 'rb'))

    data = property(_get_internal_data, _set_internal_data)

    def get_current_source_num(self):
        """Get current source num.

        Returns an integer.
        """
        return self.data['curr_src_num']

    def set_current_source_num(self, num):
        """Set current source num.
        """
        self._data['curr_src_num'] = num
        self.data = self._data
        return

    def get_current_repr_num(self, num):
        """Get current representation num for source number `num`.

        Get the current number of representations stored for source
        numer `num`. `num` is expected to be an integer.

        Returns an integer.
        """
        return self.data['curr_repr_num'].get(str(num), 0)

    def set_current_repr_num(self, num, value):
        """Set current representation num for source number `num` to `value`.

        Indicate, that source number `num` has `value`
        representations. Both paramters are expected to be integers.
        """
        self._data['curr_repr_num'].update([(str(num), value), ])
        self.data = self._data
        return

    def create(self):
        """Create the default dirs for this bucket.

        This method is called when instantiating a bucket.

        You should therefore be aware that constructing a bucket will
        try to modify the file system.
        """
        for path in (self.path, self.srcdir, self.resultdir, self.keysdir):
            if os.path.exists(path):
                continue
            os.makedirs(path)
        return

    def get_stored_source_num(self, src_path):
        """Tell whether a file like that in `src_path` is already stored.

        A stored one and the file in `src_path` are compared by
        content. That means that `os.stat` attributes, filename,
        etc. do not matter.

        Returns the number of the stored source if found, `None` else.
        """
        for name in os.listdir(self.srcdir):
            if filecmp.cmp(
                os.path.join(self.srcdir, name), src_path, shallow=False):
                return int(name.split('_')[-1])
        return None

    def get_stored_repr_num(self, src_num, repr_key):
        """Find a representation number for source number `src_num`.

        If for source number `src_num` a representation with key
        `repr_key` is stored already in bucket, the number of the
        respective representation will be returned.

        If no such key can be found for the given source, you will get
        ``None``.
        """
        keydir = os.path.join(self.keysdir, str(src_num))
        if not os.path.isdir(keydir):
            return None
        for name in os.listdir(keydir):
            keypath = os.path.join(keydir, name)
            f1 = open(keypath, 'rb')
            f2 = repr_key
            if isinstance(f2, str):
                f2 = StringIO(repr_key)
            if filelike_cmp(f1, f2):
                return int(name.split('.')[0])
        return None

    def store_representation(self, src_path, repr_path, repr_key=''):
        """Store a representation for a source under a representation
        key.

        `repr_key` can be a string or some file-like object already
        opened for reading.

        Sources are only stored really if they do not exist already.

        A source is considered to be already stored, if both, the
        contents of the file given in `src_path` and the contents of
        an already stored file are equal.

        Representations and their respective files are created if they
        do not exist already or *overwritten* otherwise.

        A representation is considered to exist already, if a
        representation with the same `repr_key` as passed in is
        already stored.

        Returns a bucket key.
        """
        src_num = self.get_stored_source_num(src_path)
        if src_num is None:
            # create new source
            src_num = self.get_current_source_num() + 1
            shutil.copy2(
                src_path, os.path.join(self.srcdir, 'source_%s' % src_num))
            self.set_current_source_num(src_num)
            os.makedirs(os.path.join(self.keysdir, str(src_num)))
        repr_num = self.get_stored_repr_num(src_num, repr_key)
        if repr_num is None:
            # store new key
            repr_num = self.get_current_repr_num(src_num) + 1
            self.set_current_repr_num(src_num, repr_num)
            key_path = os.path.join(
                self.keysdir, str(src_num), '%s.key' % repr_num)
            write_filelike(repr_key, key_path)
        # store/update representation
        repr_dir = os.path.join(
            self.resultdir, str(src_num), str(repr_num))
        if os.path.exists(repr_dir):
            shutil.rmtree(repr_dir)  # remove any old representation
        os.makedirs(repr_dir)
        shutil.copy2(repr_path, repr_dir)
        return '%s_%s' % (src_num, repr_num)

    def get_representation(self, bucket_key):
        """Get path to representation identified by `bucket_key`.

        If no such representation is stored, ``None`` is returned.
        """
        src_num, repr_num = bucket_key.split('_')
        repr_dir = os.path.join(self.resultdir, src_num, repr_num)
        if not os.path.isdir(repr_dir):
            return None
        basename = os.listdir(repr_dir)[0]
        return os.path.join(repr_dir, basename)

    def keys(self):
        """Get a generator of all bucket keys available in this bucket.
        """
        for src_num in os.listdir(self.resultdir):
            for repr_num in os.listdir(os.path.join(
                self.resultdir, src_num)):
                yield '%s_%s' % (src_num, repr_num)


class CacheManager(object):
    """A cache manager.

    This cache manager caches processed files and their sources. It
    uses hashes and buckets to find paths of cached files quickly.

    Overall it maps input files plus a (maybe huge) key on output
    files. The cache manager is interesting when the computation of an
    output file is expensive but must be repeated often.

    A sample application is to cache converted office files: as the
    computation is expensive, we can store the results of conversion
    in the cache manager and get it any time we want much more
    quickly. See cachemanager.txt for more infos.

    It also checks for hash collisions: if two input files give the
    same hash, they will be handled correctly.
    """
    def __init__(self, cache_dir, level=1):
        self.cache_dir = cache_dir
        self._prepare_cache_dir()
        self.level = level  # How many dir levels will we create?

    def _prepare_cache_dir(self):
        """Prepare the cache dir, create dirs, etc.
        """
        cache_dir = self.cache_dir

        if cache_dir is None:
            return

        cache_dir = os.path.abspath(cache_dir)

        if os.path.exists(cache_dir) and not os.path.isdir(cache_dir):
            raise IOError('not a dir but a file: %s' % cache_dir)

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
            # XXX: log this
            #sys.stderr.write('Create cachedir: %s\n' % cache_dir)
        self.cache_dir = cache_dir
        return

    @classmethod
    def _compose_cache_key(cls, hash_digest, bucket_key):
        """Get an official marker.

        The cache manager's 'official' key consists of a hash_digest,
        and a bucket key (which is maintained by the bucket alone).

        You should not make any assumptions about how the key is
        constructed from these strings.
        """
        return "%s_%s" % (hash_digest, bucket_key)

    @classmethod
    def _dissolve_cache_key(cls, cache_key):
        """Extract a hashdigest and a bucket key from `cache_key`.

        A `cache_key` consists of a hash digest and a bucket key. Both
        parts here are extracted from the given string if possible and
        returned as a tuple ``(<hash_digest>, <bucket-key>)``.

        Both items of the tuple can be ``None`` if they could not be
        extracted.
        """
        if not isinstance(cache_key, str):
            return (None, None)
        if not '_' in cache_key:
            return (None, None)
        return cache_key.split('_', 1)

    def _get_bucket_path(self, hash_digest):
        """Get a bucket in which a source with 'hash_digest' would be stored.

        .. note:: This call creates the appropriate bucket in
                  filesystem if it does not exist already!

        """
        dirs = [hash_digest[x * 2:x * 2 + 2]
                for x in range((self.level + 1))][:-1]
        dirs.append(hash_digest)
        bucket_path = os.path.join(self.cache_dir, *dirs)
        return bucket_path

    @classmethod
    def get_hash(cls, path):
        """Get the hash of a file stored in ``path``.

        Currently we compute the MD5 digest.

        Note for derived classes, that the hash digest computed by
        this method should give only chars that can easily be
        processed as path elements in URLs. For instance slashes
        (which can occur in Base64 encoded strings) could make things
        difficult.
        """
        hash_value = md5()
        with open(path, 'rb') as bin_file:
            # read file in chunks of 512 bytes as md5 processes chunks
            # of 128 bytes and filesystems like chunks of 512 bytes
            for chunk in iter(lambda: bin_file.read(512), b''):
                hash_value.update(chunk)
        return hash_value.hexdigest()

    def get_cached_file(self, cache_key):
        """Get the representation stored for `cache_key`.

        Returns the path to a file represented by `cache_key` or
        ``None`` if no such representation is stored in cache already.
        """
        hash_digest, bucket_key = self._dissolve_cache_key(cache_key)
        if hash_digest is None:
            return None
        bucket_path = self._get_bucket_path(hash_digest)
        if bucket_path is None or not os.path.exists(bucket_path):
            return None
        bucket = Bucket(bucket_path)
        return bucket.get_representation(bucket_key)

    def get_cached_file_by_source(self, source_path, repr_key=''):
        """Get the representation stored for a source file and a key.

        .. versionadded:: 1.1

        Returns ``(<path>, <cache_key>)`` where ``<path>`` is the path
        to a file represented by `source_path` and
        `repr_key`. ``<cache_key>`` is the key you can use with
        :meth:`get_cached_file` to get cached files much quicker. Both
        values are ``None`` if no such representation is stored in
        cache already.

        Does basically the same as :meth:`get_cached_file` but without
        a cache_key. Instead the source file is examined again and we
        look for a representation matching the repr_key. In other
        words: we find docs that have been registered already with
        source file and repr_key.

        .. note:: This method is much more expensive than
                  :meth:`get_cached_file`. Please use it only if the
                  ``cache_key`` cannot be determined otherwise.

        """
        hash_digest = self.get_hash(source_path)
        bucket = Bucket(self._get_bucket_path(hash_digest))
        src_num = bucket.get_stored_source_num(source_path)
        if src_num is None:
            return None, None
        repr_num = bucket.get_stored_repr_num(src_num, repr_key)
        if repr_num is None:
            return None, None
        bucket_key = '%s_%s' % (src_num, repr_num)
        cache_key = self._compose_cache_key(hash_digest, bucket_key)
        return bucket.get_representation(bucket_key), cache_key

    def register_doc(self, source_path, to_cache, repr_key=''):
        """Store a representation of file found in `source_path` which
        resides in path `to_cache` to a bucket.

        `repr_key` can be a string or a file-like object opened for
        reading. It must be unique for that very special
        representation of the file in `source_path`.

        Returns a marker string which can be used in connection with
        the appropriate cache manager methods to retrieve the
        representation later on.
        """
        md5_digest = self.get_hash(source_path)
        bucket = Bucket(self._get_bucket_path(md5_digest))
        bucket_key = bucket.store_representation(
            source_path, to_cache, repr_key=repr_key)
        return self._compose_cache_key(md5_digest, bucket_key)

    def keys(self):
        """Get a list of all cache keys currently available.
        """
        glob_expr = self.cache_dir + (b'/*' * (self.level + 1))
        for path in glob.glob(glob_expr):
            md5_hash = os.path.basename(path)
            bucket = Bucket(path)
            for bucket_key in bucket.keys():
                yield '%s_%s' % (md5_hash, bucket_key)
