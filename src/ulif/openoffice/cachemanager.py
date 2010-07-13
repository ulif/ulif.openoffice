##
## cachemanager.py
## Login : <uli@pu.smp.net>
## Started on  Mon Sep  7 13:48:00 2009 Uli Fouquet
## $Id$
## 
## Copyright (C) 2009 Uli Fouquet
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
"""A manager for storing generated files.
"""
import filecmp
try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5 # Deprecated since Python 2.5
import os
import re
import shutil
import sys
import cPickle as pickle

HASH_DIGEST_FORM = re.compile('^[0-9a-z]{32}$')
LEVEL_FORM = re.compile('^[0-9a-z]{2}$')

def internal_suffix(suffix=None):
    """The suffix used internally in buckets.
    """
    if suffix is None:
        return 'default'
    return '_' + suffix

class Bucket(object):
    """A bucket where we store files with same hash sums.

    .. warning:: :class:`Bucket` is not thread-safe!

    Buckets store 'source' files and their representations. A
    representation is simply another file, optionally marked with a
    'suffix'. This is meant to be used like a certain office document
    (the 'source' file) for which different converted representations
    (for instance an HTML, or PDF version) might be stored.

    For each source file there can be an arbitrary number of
    representations, as long as each representation provides a
    different 'suffix'. The :class:`Bucket` does not introspect the
    files and makes no assumptions about the file-type or format. So,
    you could store a PDF representation with an 'xhtml' suffix if you
    like.

    The 'suffix' for a representation is a simple string and can be
    chosen by the user. Normally, you would choose something like
    'pdf' for a PDF version of a certain source file.

    Each bucket can hold several source files and knows which
    representations belong to which source file.

    To make a distinction between different sources inside the same
    bucket, the bucket manages 'markers' which normally are simple
    stringified numbers, one for each source and the representations
    connected to it. You should, however, make no assumptions about
    the marker, except that it is a string.

    Currently, you can store as much source files in a bucket, as the
    the maximum integer number can address.
    """
    
    def __init__(self, path):
        self.path = path
        self.srcdir = os.path.join(self.path, 'sources')
        self.resultdir = os.path.join(self.path, 'results')
        self.create()
        if self.data is None:
            self.data = dict(
                version=0,
                current_num=0,
                )
        self._data = self.data

    def _setInternalData(self, data):
        data_path = os.path.join(self.path, 'data')
        pickle.dump(data, open(data_path, 'wb'))
        return

    def _getInternalData(self):
        data_path = os.path.join(self.path, 'data')
        if not os.path.exists(data_path):
            return None
        return pickle.load(open(data_path, 'rb'))

    data = property(_getInternalData, _setInternalData)
    
    def getCurrentNum(self):
        """Get current source num.
        """
        return self.data['current_num']

    def setCurrentNum(self, num):
        """Set current source num.
        """
        self._data['current_num'] = num
        self.data = self._data
        return

    def create(self):
        """Create the default dirs for this bucket.

        This method is called when instantiating a bucket.

        You should therefore be aware that constructing a bucket will
        try to modify the file system.
        """
        for path in (self.path, self.srcdir, self.resultdir):
            if os.path.exists(path):
                continue
            os.makedirs(path)
        return

    def getSourcePath(self, path):
        """Get a path to a source file that equals file stored in path.

        Returns a tuple (path, marker) or (None, None) if the source
        cannot be found.
        """
        names = os.listdir(self.srcdir)
        for filename in names:
            src_path = os.path.join(self.srcdir, filename)
            filename_parts = filename.split('_', 2)
            if len(filename_parts) < 2:
                continue
            if not filename.startswith('source'):
                continue
            if not filecmp.cmp(path, src_path, shallow=False):
                continue
            marker = filename_parts[1]
            return src_path, marker
        return (None, None)

    def getResultPath(self, path, suffix=None):
        """Get the cached result for path.
        """
        marker = None
        suffix = internal_suffix(suffix)
        src_path, marker = self.getSourcePath(path)
        if src_path is None:
            return None
        result_filename = 'result_%s_%s' % (marker, suffix)
        result_path = os.path.join(self.resultdir, result_filename)
        if os.path.exists(result_path) and os.path.isfile(result_path):
            return result_path
        return None

    def storeResult(self, src_path, result_path, suffix=None):
        """Store file in ``result_path`` as representation of source in
        ``src_path``.

        Optionally store this result marked with a certain ``suffix``
        string.

        The result has to be a path to a single file.

        If `suffix` is given, the representation will be stored marked
        with the suffix in order to be able to distinguish this
        representation from possible others.

        If the source file given by `src_path` already exist in the
        bucket, the file in `result_path` will be stored as a
        representation of the already existing source file.

        We determine wether an identical source file already exists in
        the bucket by comparing the given file in `src_path` with the
        source files already stored in the bucket byte-wise.
        """
        suffix = internal_suffix(suffix)
        local_source, marker = self.getSourcePath(src_path)
        if local_source is None:
            # Create new source
            num = self.getCurrentNum()
            num += 1
            self.setCurrentNum(num)
            marker = str(num)
            local_source = os.path.join(
                self.srcdir, 'source_%s' % marker)
            shutil.copyfile(src_path, local_source)
                
        # Store result file
        result_filename = 'result_%s_%s' % (marker, suffix)
        local_result = os.path.join(self.resultdir, result_filename)
        shutil.copyfile(result_path, local_result)
        return marker

    def getAllSourcePaths(self):
        """Get the paths of all source files stored in this bucket.

        Returns a generator of paths.
        """
        for filename in os.listdir(self.srcdir):
            src_path = os.path.join(self.srcdir, filename)
            filename_parts = filename.split('_', 2)
            if len(filename_parts) < 2:
                continue
            if not filename.startswith('source'):
                continue
            #marker = filename_parts[1]
            yield src_path
        #yield (None, None)

    def getResultPathFromMarker(self, marker, suffix=None):
        """Get path of a result file stored with marker ``marker`` and suffix
        ``suffix``

        If the path does not exist ``None`` is returned.
        """
        suffix = internal_suffix(suffix)
        result_filename = 'result_%s_%s' % (marker, suffix)
        local_result = os.path.join(self.resultdir, result_filename)
        if os.path.isfile(local_result):
            return local_result
        return None

class CacheManager(object):
    """A cache manager.

    This cache manager caches processed files and their sources. It
    uses hashes and buckets to find paths of cached files quickly.

    Overall it maps input files on output files. The cache manager is
    interesting when the computation of an output file is expensive
    but must be repeated often.

    A sample application is to cache converted office files: as the
    computation is expensive, we can store the results of conversion
    in the cache manager and get it any time we want much more
    quickly. See cachemanager.txt for more infos.

    It also checks for hash collisions: if two input files give the
    same hash, they will be handled correctly.
    """
    def __init__(self, cache_dir, level=1):
        self.cache_dir = cache_dir
        self.prepareCacheDir()
        self.level = level # How many dir levels will we create?

    def _composeMarker(self, hash_digest, bucket_marker):
        """Get an official marker.

        The cache manager's 'official' maker consists of a
        hash_digest, a bucket marker (which is maintained by the
        bucket alone) and a suffix.

        You should not make any assumptions about how the marker is
        constructed from these strings.
        """
        if bucket_marker is not None:
            bucket_marker = '_%s' % bucket_marker
        else:
            bucket_marker = ''
        return "%s%s" % (hash_digest, bucket_marker)

    def _dissolveMarker(self, marker):
        """Extract a hashdigest and a bucket marker from marker.

        A marker consists of a hash digest and a bucket marker. Both
        parts here are extracted from a marker string if possible and
        returned as a tuple ``(<hash_digest>, <bucket-marker>)``.

        Both items of the tuple can be ``None`` if they could not be
        extracted.
        
        """
        if not isinstance(marker, basestring):
            return (None, None)
        if not '_' in marker:
            return (None, None)
        return marker.split('_', 1)
    
    def _getBucketPathFromPath(self, path):
        """Get a bucket path from a path to a sourcefile.

        This does not modify the filesystem.
        """
        hash_digest = self.getHash(path)
        return self._getBucketPathFromHash(hash_digest)

    def _getBucketPathFromHash(self, hash_digest):
        """Get a bucket path from hash.

        If a path cannot be computed (due to faulty hash or similar),
        ``None`` is returned.
        """
        if len(hash_digest) != 32:
            return None
        dirs = [hash_digest[x*2:x*2+2]
                for x in range((self.level+1))][:-1]
        dirs.append(hash_digest)
        bucket_path = os.path.join(self.cache_dir, *dirs)
        return bucket_path

    def prepareCacheDir(self):
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
            sys.stderr.write('Create cachedir: %s\n' % cache_dir)
        self.cache_dir = cache_dir
        return

    def getBucketFromPath(self, path):
        """Get a bucket in which the source given by path would be stored.

        .. note:: This call creates the appropriate bucket in
                  filesystem if it does not exist already!

        """
        md5_digest = self.getHash(path)
        return self.getBucketFromHash(md5_digest)
    
    def getBucketFromHash(self, hash_digest):
        """Get a bucket in which a source with 'hash_digest' would be stored.

        .. note:: This call creates the appropriate bucket in
                  filesystem if it does not exist already!

        """
        dirs = [hash_digest[x*2:x*2+2]
                for x in range((self.level+1))][:-1]
        dirs.append(hash_digest)
        bucket_path = os.path.join(self.cache_dir, *dirs)
        return Bucket(bucket_path)

    def getCachedFile(self, path, suffix=None):
        """Check, whether the file in ``path`` is already cached.

        Returns the path of cached file or ``None``. Only 'result'
        files are looked up and returned, not sources.

        This method does not modify the filesystem if an appropriate
        bucket does not yet exist.
        """
        bucket_path = self._getBucketPathFromPath(path)
        if not os.path.exists(bucket_path):
            return None
        bucket = Bucket(bucket_path)
        return bucket.getResultPath(path, suffix=suffix)

    def getCachedFileFromMarker(self, marker, suffix=None):
        """Check whether a basket exists for marker and suffix.

        Returns the path to a file represented by that marker or
        ``None``.
        
        A basket exists, if there was already registered a doc, which
        returned that marker on registration.

        The basket might contain a representation of type ``suffix``.
        If this is true, the path to the file is returned, ``None``
        else.
        """
        hash_digest, bucket_marker = self._dissolveMarker(marker)
        if hash_digest is None:
            return None
        bucket_path = self._getBucketPathFromHash(hash_digest)
        if bucket_path is None:
            return None
        if not os.path.exists(bucket_path):
            return None
        bucket = Bucket(bucket_path)
        return bucket.getResultPathFromMarker(
            bucket_marker, suffix=suffix)

    def registerDoc(self, source_path, to_cache, suffix=None):
        """Store a representation of file found in ``source_path`` which
        resides in ``to_cache`` to a bucket.

        If ``suffix`` is not ``None`` the representation will be
        stored under the suffix name. A suffix is only a name and the
        cache manager makes no assumptions about file types or
        similar.

        Returns a marker string which can be used in conjunction with
        the appropriate cache manager methods to retrieve the file
        later on.
        """
        md5_digest = self.getHash(source_path)
        bucket = self.getBucketFromHash(md5_digest)
        bucket_marker = bucket.storeResult(source_path, to_cache,
                                           suffix=suffix)
        return self._composeMarker(md5_digest, bucket_marker)

    def getHash(self, path):
        """Get the hash of a file stored in ``path``.

        Currently we compute the MD5 digest.

        Note for derived classes, that the hash digest computed by
        this method should give only chars that can easily be
        processed as path elements in URLs. For instance slashes
        (which can occur in Base64 encoded strings) could make things
        difficult.
        """
        hash_value = md5()
        hash_value.update(open(path, 'r').read())
        return hash_value.hexdigest()

    def contains(self, path=None, marker=None, suffix=None):
        """Check, whether the file in ``path`` or marked by ``marker`` and
        with suffix ``suffix`` is already cached.

        This is a convenience method for easy checking of caching
        state for certain files. You can also get the information by
        using other API methods of :class:`CacheManager`.

        You must at least give one of ``path`` or ``marker``, not
        both.

        The ``suffix`` parameter is optional.

        Returns ``True`` or ``False``.
        """
        if path is None and marker is None:
            raise TypeError(
                "contains() takes at least one of `path' or `marker'")
        if path is not None and marker is not None:
            raise TypeError(
                "contains() takes only one of `path' or `marker', not both")
        result_path = None
        if marker is not None:
            result_path = self.getCachedFileFromMarker(marker, suffix=suffix)
        else:
            result_path = self.getCachedFile(path, suffix=suffix)
        return result_path is not None

    def getAllSources(self, parent=None, level=0):
        """Return all source documents.
        """
        if parent is None:
            parent = self.cache_dir
        names = os.listdir(parent)
        for name in names:
            full_path = os.path.join(parent, name)
            if level < self.level:
                if not os.path.isdir(full_path):
                    continue
                if LEVEL_FORM.match(name) is None:
                    continue
                for x in self.getAllSources(full_path, level + 1):
                    yield x
                continue
            if HASH_DIGEST_FORM.match(name) is None:
                continue
            bucket = self.getBucketFromHash(name)
            for path in bucket.getAllSourcePaths():
                yield path
