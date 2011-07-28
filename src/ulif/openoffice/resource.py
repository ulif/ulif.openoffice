##
## resource.py
## Login : <uli@pu.smp.net>
## Started on  Wed Apr 27 01:12:21 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
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
"""
Resources for servers.
"""
import os
import shutil
import tempfile
from urlparse import urlparse
from ulif.openoffice.convert import convert_to_html

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5 # Deprecated since Python 2.5

class Resource(object):
    """A resource contains data.
    """

    def __init__(self, workdir, params=None):
        self.workdir = workdir
        self.params = params
        return

    def _get_data(self):
        return None

    def getData(self):
        pass

def copy_to_secure_location(path):
    dir = tempfile.mkdtemp()
    new_loc = os.path.join(dir, os.path.basename(path))
    shutil.copy2(path, new_loc)
    return (new_loc, dir)

def create_resource(file_path, cache_manager=None, params=None):
    """Try to create a resource.

    Returns a triple ``(<STATUS>, <HASH>, <PATH>)``.
    """
    if not isinstance(file_path, basestring):
        return (None, None, None)
    new_loc, dir = copy_to_secure_location(file_path)
    status, hash, path = process_file(
        new_loc, cache_manager=cache_manager, params=params)
    if path is None:
        shutil.rmtree(dir)
    return (status, hash, path)

def get_resource(cache_manager=None, doc_id=None, params=None):
    if cache_manager is None:
        # No cache, no results...
        return None
    return

def process_file(path, cache_manager=None, params=None):
    status, result_paths = convert_to_html(path=path)
    if status != 0:
        return status, None, None
    result_path = result_paths[0]
    if isinstance(result_path, basestring):
        result_path = urlparse(result_path).path
    # Remove original file if still existing...
    if os.path.exists(path) and os.path.isfile(path):
        os.unlink(path)
    hash = params_to_hash(params)
    return status, hash, result_path

def params_to_hash(params):
    normalized = normalized_params(params)
    return md5("%s" % normalized).hexdigest()

def normalized_params(params):
    return params
