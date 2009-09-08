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
import md5 # Deprecated but works also with Python2.4...
import os
import shutil
import sys

class CacheManager(object):

    def __init__(self, cache_dir, level=1):
        self.cache_dir = cache_dir
        self.prepareCacheDir()
        self.level = level # How many dir levels will we create?

    def prepareCacheDir(self):
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

    def contains(self, extension=None, data=None, path=None):
        """Tell whether a document is stored.

        You must pass ``extension`` and either ``data`` or ``path``.
        """
        if extension is None:
            raise ValueError('extension must not be None.')
        if data is None and path is None:
            raise ValueError('either path or data must be given.')
        if not data is None and not path is None:
            raise ValueError('only one of data or path might be given')
        md5_digest = self.getMD5Digest(data=data, path=path)
        dir = self.getCacheDir(extension=extension, md5_digest=md5_digest)
        if not os.path.exists(dir):
            return False
        return True

    def getMD5Digest(self, data=None, path=None):
        """Get the MD5 sum of a file.

        You can pass the file contents (``data``) **or** the ``path``.
        """
        if data is not None:
            return md5.new(data).hexdigest()
        return md5.new(open(path, 'r').read()).hexdigest()

    def getCacheDir(self, extension, md5_digest):
        """Get the cache dir where a document with given parameters would be
           stored.

        This does not guarantee, that the path really exists.
        """
        parent_dir = [md5_digest[x*2:x*2+2]
                      for x in range((self.level+1))][:-1]
        parent_dir.append(md5_digest)
        extension = extension.lower()
        parent_cache_dir = os.path.join(*parent_dir)
        parent_cache_dir = os.path.join(
            self.cache_dir, parent_cache_dir, extension)
        return parent_cache_dir

    def registerDoc(self, source_path, to_cache):
        """Register the document at path ``to_cache`` generated from
           ``source_path``.

           Both paths should refer to files, not directories.
        """
        md5_digest = self.getMD5Digest(path=source_path)
        ext = os.path.splitext(to_cache)[1][1:].lower()
        dir = self.getCacheDir(ext, md5_digest)

        if ext in ['pdf',]:
            # Copy only the result doc...
            dst_dir = dir
            dst = os.path.join(dir, os.path.basename(to_cache))
            os.makedirs(dir)
            shutil.copy2(to_cache, dst)
            return
        # Copy all files in result dir...
        dir_to_cache = os.path.dirname(to_cache)
        os.makedirs(dir)
        for filename in os.listdir(dir_to_cache):
            fullpath = os.path.join(dir_to_cache, filename)
            if not os.path.isfile(fullpath):
                # Ignore subdirs.
                continue
            if filename == os.path.basename(source_path):
                # Ignore source document.
                continue
            dst = os.path.join(dir, filename)
            shutil.copy2(fullpath, dst)
        return

    def getCachedDocPath(self, source_path, ext):
        """Get a cached docs path or ``None``.
        """
        md5_digest = self.getMD5Digest(path=source_path)
        ext = ext.lower()
        dir = self.getCacheDir(ext, md5_digest)
        if not os.path.isdir(dir):
            return None
        cached_file = os.path.basename(source_path)
        cached_file = os.path.splitext(cached_file)[0] + '.' + ext
        return os.path.join(dir, cached_file)
