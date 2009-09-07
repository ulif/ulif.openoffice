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
import os
import sys

class CacheManager(object):

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.prepareCacheDir()

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
