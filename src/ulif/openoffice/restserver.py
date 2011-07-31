##
## restserver.py
## Login : <uli@pu.smp.net>
## Started on  Wed Apr 20 03:01:13 2011 Uli Fouquet
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
RESTful server (cherry.py flavour)
"""
import os
import sys
import tempfile
import cherrypy
from optparse import OptionParser
from ulif.openoffice.cachemanager import (
    CacheManager, CACHE_SINGLE, CACHE_PER_USER)
from ulif.openoffice.helpers import (
    remove_file_dir, get_entry_points, string_to_bool, base64url_encode)
from ulif.openoffice.oooctl import check_port
from ulif.openoffice.processor import MetaProcessor
from ulif.openoffice.util import get_content_type

def get_marker(options=dict()):
    """Compute a unique marker for a set of options.

    The returned marker is a string suitable for use in
    filessystems. Different sets of options will result in different
    markers where order of options does not matter.

    In :mod:`ulif.openoffice` we use the marker to feed the cache
    manager.
    """
    result = sorted(options.items())
    result = '%s' % result
    return base64url_encode(result).replace('=', '')

def get_cached_doc(input, options, cache_dir=None):
    """Return a cached document for input if available.

    The returned string is the resultpath of the cached document. If
    no such path can be found, you get ``None``.
    """
    if cache_dir is None:
        return None
    marker = get_marker(options)
    cm = CacheManager(cache_dir)
    return cm.getCachedFile(input, marker)

def cache_doc(input, output, marker, cache_dir=None,):
    """Store generated file in cache.

    `input` and `output` are paths giving the output file created from
    input file. `marker` is the (distinct) 'suffix' under which we
    store different output files for same `input`. `cache_dir` is the
    path to the cache.
    """
    if cache_dir is None:
        return
    cm = CacheManager(cache_dir)
    cm.registerDoc(
        source_path=input, to_cache=output, suffix=marker)
    return

def mangle_allow_cached(data, default=True):
    """Pick ``allow_cached`` keyword from data.

    If the mentioned keyword is part of data dict, turn its string
    value unto bool (default as per `default` parameter) and
    return this value.
    """
    allow = string_to_bool(data.get('allow_cached', default))
    if 'allow_cached' in data.keys():
        del data['allow_cached']
    if allow is None:
        allow = default
    return allow

def get_cachedir(allow_cached, cache_dir, cache_layout, user):
    if cache_dir is None or not allow_cached:
        return None
    if cache_layout == CACHE_PER_USER:
        cache_dir = os.path.join(cache_dir, user)
    return cache_dir

def process_doc(doc, data, cached_default, cache_dir, cache_layout, user):
    allow_cached = mangle_allow_cached(data, cached_default)
    result_path = None
    metadata = dict(error=False, cached=False)
    if allow_cached and cache_dir is not None:
        # Ask cache for already stored copy
        real_cachedir = get_cachedir(
            allow_cached, cache_dir, cache_layout, user)
        result_path = get_cached_doc(doc, data, cache_dir=cache_dir)
        cached_result = True
    if result_path is None:
        # Generate result
        proc = MetaProcessor(options=data)
        result_path, metadata = proc.process(doc)
        cached_result = False
    return result_path, metadata, cached_result

class DocumentRoot(object):
    exposed = True

    def __init__(self, cache_dir=None, cache_layout=CACHE_SINGLE):
        self.cache_dir = cache_dir
        self.cache_layout = cache_layout
        return

    def not_cp_dispatch(self, vpath):
        if vpath:
            doc_id = vpath.pop(0)
            #cherrypy.request.params['doc_id'] = doc_id
            if doc_id == 'index':
                return DocumentIndex(
                    cache_dir = self.cache_dir, cache_layout=self.cache_layout)
            return Document(doc_id, cache_dir=self.cache_dir)
            #if doc_id in self.doc_ids:
            #    return Document(doc_id)
            #elif doc_id == 'index':
            #    return DocumentIndex(self.doc_ids)
        if vpath:
            return getattr(self, vpath[0], None)
        return

    def POST(self, doc=None, **data):
        """Create a resource (converted document) and return it.
        """

        if doc is None:
            raise cherrypy.HTTPError(
                400, 'Request must contain `doc` parameter')
        if getattr(doc, 'filename', None) is None:
            raise cherrypy.HTTPError(
                400, '`doc` must be a file')

        # Create a filesystem copy of the file retrieved
        workdir = tempfile.mkdtemp()
        file_path = os.path.join(workdir, doc.filename)
        open(file_path, 'wb').write(doc.file.read())

        # Process input
        user = cherrypy.request.login  # Maybe None

        # allow_cached = self.mangle_allow_cached(data)
        # result_path = None
        # metadata = dict(error=False, cached=False)
        # #if allow_cached and self.cachedir is not None:
        #     # Ask cache for already stored copy
        #     #local_cachedir = get_cachedir(
        #     #    self.cache_dir, allow_cached, self.cache_layout, user)
        #     #result_path = get_cached_doc(file_path, data, cachedir=cache_dir)
        # #if result_path is None:
        # proc = MetaProcessor(options=data)
        # result_path, metadata = proc.process(file_path)
        result_path, metadata, cached_result = process_doc(
            file_path, data, True, self.cache_dir, self.cache_layout, user)

        if not isinstance(result_path, basestring):
            return self.handle_error(metadata, workdir)
        if metadata.get('error', False) is True:
            return self.handle_error(metadata, workdir)
        basename = os.path.basename(result_path)
        content_type = get_content_type(result_path)

        # Create temporary return file
        result_file = tempfile.TemporaryFile()
        result_file.write(open(result_path, 'rb').read())
        result_file.flush()
        result_file.seek(0)

        # Remove obsolete files/dirs
        remove_file_dir(result_path)
        remove_file_dir(workdir)
        return cherrypy.lib.static.serve_fileobj(
            result_file, content_type=content_type, name=basename)

    def handle_error(self, metadata, workdir):
        msg = metadata.get('error-descr', 'No error description available')
        remove_file_dir(workdir)
        raise cherrypy.HTTPError(503, msg)


class Document(object):
    def _cp_dispatch(self, vpath):
        return getattr(self, vpath[0], None)
    exposed = True

    def __init__(self, doc_id, cache_manager=None):
        self.cache_manager = None
        self.doc_id = doc_id
        return

    def GET(self):
        return "Hi from doc %s" % self.doc_id

class DocumentIndex(object):
    exposed = True
    def _cp_dispatch(self, vpath):
        return getattr(self, vpath[0], None)

    def __init__(self, cache_manager=None, cache_layout=CACHE_SINGLE):
        self.cache_manager = cache_manager

    def GET(self):
        return """
          <html>
           <body>
           Available IDs: %s <br />
           <form action="/docs" method="POST">
             ID: <input type="text" name="doc_id"> <br />
             <input type="submit" name="SUBMIT" value="Add">
           </form>
           </body>
          </html>
          """ % self.ids

class Status(object):

    exposed = True

    @property
    def avail_procs(self):
        return get_entry_points('ulif.openoffice.processors')

    def GET(self):
        content = "<html><body>"
        content += "<h1>Status Report</h1>"
        content += "<h2>Installed doc processors: </h2>"
        content += "<table><thead><tr><th>name</th><th>defaults</th>"
        content += "</tr></thead><tbody>"
        for name, proc in self.avail_procs.items():
            content += "<tr><td>%s</td><td>%s</td></tr>" %(
                name, proc.defaults)
        content += "</tbody></table>"
        content += "<h2>OpenOffice.org/LibreOffice Server:</h2>"
        content += "<table><thead><tr><th>key</th><th>value</th>"
        content += "</tr></thead><tbody>"
        content += '<tr><td>Status</td><td id="ooo_status">%s</td></tr>' %(
            check_port('localhost', 2002) and 'UP' or 'DOWN', )
        content += "</tbody></table>"
        content +="</body></html>"
        return content

class Root(object):

    @property
    def docs(self):
        return DocumentRoot(
            cache_dir=self.cache_dir, cache_layout=self.cache_layout)

    status = Status()

    def __init__(self, cache_dir=None, cache_layout=CACHE_SINGLE):
        self.cache_dir = cache_dir
        self.cache_layout = cache_layout
        return

userpassdict = {'bird' : 'bebop', 'ornette' : 'wayout'}
checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(userpassdict)

root = Root()

DEFAULT_CONFIG = {
    'global': {
        'server.socket_host': 'localhost',
        'server.socket_port': 8000,
        },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        #'tools.auth_basic.on': True,
        'tools.auth_basic.realm': 'ulif.openoffice restful document server',
        'tools.auth_basic.checkpassword': checkpassword,
        }
    }

def main(argv=sys.argv):
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-c", "--config", dest="config",
                      help="use CONFIG as configuration file.",
                      default=DEFAULT_CONFIG)
    parser.add_option("-d", "--daemonize", dest="daemonize",
                      help="run server as a daemon.",
                      action="store_true",
                      default=False)
    parser.add_option("-p", "--cacheurl", dest="cachedir",
                      help="use CACHEURL to cache results.",
                      default=None)
    (options, args) = parser.parse_args(argv[1:])

    from cherrypy.process.plugins import Daemonizer
    if options.daemonize is True:
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    cherrypy.quickstart(Root(cache_dir=options.cachedir), '/', options.config)
