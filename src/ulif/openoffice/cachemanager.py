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
    import hashlib
    md5 = None
except ImportError:
    import md5 # Deprecated since Python 2.5
    hashlib = None
import os
import shutil
import sys
import cPickle as pickle

def internal_suffix(suffix=None):
    """The suffix used internally in buckets.
    """
    if suffix is None:
        return 'default'
    return '_' + suffix

class Bucket(object):
    """A bucket where we store files with same hash sums.
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
        for filename in os.listdir(self.srcdir):
            src_path = os.path.join(self.srcdir, filename)
            filename_parts = filename.split('_', 2)
            if len(filename_parts) < 2:
                continue
            if not filename.startswith('source'):
                continue
            if not filecmp.cmp(path, src_path):
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
        filename = os.path.basename(src_path)
        result_filename = 'result_%s_%s' % (marker, suffix)
        result_path = os.path.join(self.resultdir, result_filename)
        if os.path.exists(result_path) and os.path.isfile(result_path):
            return result_path
        return None

    def storeResult(self, src_path, result_path, suffix=None):
        """Store file in result_path as result for source in src_path.

        Optionally store this result marked with a certain suffix.

        The result has to be a path to a single file.
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
            shutil.copy2(src_path, local_source)
        # Store result file
        result_filename = 'result_%s_%s' % (marker, suffix)
        local_result = os.path.join(self.resultdir, result_filename)
        shutil.copy2(result_path, local_result)
        return
        
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

    def prepareCacheDir(self):
        """Prepare the cache dir, create dirs, etc.
        """
        cache_dir = self.cache_dir

        if cache_dir is None:
            return
        
        cache_dir = os.path.abspath(cache_dir)
    
        if os.path.exists(cache_dir) and not os.path.isdir(cache_dir):
            sys.stderr.write('Cannot use cache dir. Not a directory: %s\n' % (
                    cache_dir,))
            sys.stderr.write('Caching disabled.\n')
            self.cache_dir = None
            return None

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
            sys.stderr.write('Create cachedir: %s\n' % cache_dir)
        self.cache_dir = cache_dir
        return

    def getBucketFromPath(self, path):
        """Get a bucket in which the source given by path would be stored.
        """
        md5_digest = self.getHash(path)
        return self.getBucketFromHash(md5_digest)

    def getBucketFromHash(self, hash_digest):
        """Get a bucket in which a source with 'hash_digest' would be stored.
        """
        dirs = [hash_digest[x*2:x*2+2]
                for x in range((self.level+1))][:-1]
        dirs.append(hash_digest)
        bucket_path = os.path.join(self.cache_dir, *dirs)
        return Bucket(bucket_path)

    def getCachedFile(self, path, suffix=None):
        """Check, whether the file in ``path`` is already cached.

        Returns the path of cached file or None.
        """
        bucket = self.getBucketFromPath(path)
        return bucket.getResultPath(path, suffix=suffix)

    def registerDoc(self, source_path, to_cache, suffix=None):
        """Store to_cache in bucket.
        """
        bucket = self.getBucketFromPath(source_path)
        bucket.storeResult(source_path, to_cache, suffix)
        return

    def getHash(self, path=None):
        """Get the hash of a file.

        Currently we compute the MD5 digest.
        """
        if md5 is not None:
            return md5.new(open(path, 'r').read()).hexdigest()
        hash = hashlib.new('md5')
        hash.update(open(path, 'r').read())
        return hash.hexdigest()

    def contains(self, path, suffix=None):
        """Check, whether the file in ``path`` is already cached.
        """
        return self.getCachedFile(path, suffix=suffix) is not None
