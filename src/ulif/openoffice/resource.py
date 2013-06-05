##
## resource.py
##
## Copyright (C) 2011, 2013 Uli Fouquet
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
from hashlib import md5
import os
import shutil
import tempfile
try:
    from urlparse import urlparse         # Python 2.x
except ImportError:
    from urllib import parse as urlparse  # Python 3.x
from ulif.openoffice.convert import convert


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
    if not os.path.isfile(file_path):
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
    result_dir = os.path.dirname(path)
    status, result_path = convert(
        out_format='html', path=path, out_dir=result_dir)
    if status != 0:
        return status, None, None
    if isinstance(result_path, basestring):
        result_path = urlparse(result_path).path
    # Remove original file if still existing...
    if os.path.exists(path) and os.path.isfile(path):
        os.unlink(path)
    # Determine result path of created file from returned dirname
    if os.path.exists(result_path) and os.path.isdir(result_path):
        result_path = os.path.splitext(path)[0] + '.html'
    hash = params_to_hash(params)
    return status, hash, result_path

def params_to_hash(params):
    normalized = normalized_params(params)
    return md5("%s" % normalized).hexdigest()

def normalized_params(params):
    return params
