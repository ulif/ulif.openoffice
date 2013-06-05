##
## restserver.py
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
    remove_file_dir, get_entry_points, string_to_bool, base64url_encode,
    copy_to_secure_location)
from ulif.openoffice.oooctl import check_port
from ulif.openoffice.processor import MetaProcessor
from ulif.openoffice.util import get_content_type

#
# Helper functions
#


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


def get_cached_doc(input, marker, cache_dir=None):
    """Return a cached document and its cache marker for `input` if
    available.

    If you want a special output variant of `input` you can pass
    `marker`, a string returned by cache manager when storing a
    document conversion.

    `cache_dir` is a filesystem path.

    Returns a tuple

       ``(<RESULT-PATH>, <CACHE-MARKER>)``

    where ``<RESULT-PATH>``, a string, is the resultpath of the cached
    document. If no such path can be found, you get ``None``.

    ``<CACHE-MARKER>`` is a marker you can use to retrieve the cached
    doc from the cache manager. Suitable also for etags.

    If ``<RESULT-PATH>`` is ``None``, also ``<CACHE-MARKER>`` will be
    ``None``.
    """
    etag = None
    if cache_dir is None:
        return (None, None)
    cm = CacheManager(cache_dir)
    result_path = cm.get_cached_file(input, marker)
    if result_path is not None:
        etag = cm.get_marker_from_in_cache_path(result_path)
    return result_path, etag


def cache_doc(input, output, marker, cache_dir=None,):
    """Store generated file in cache.

    `input` and `output` are paths giving the output file created from
    input file. `marker` is the (distinct) 'suffix' under which we
    store different output files for same `input`. `cache_dir` is the
    path to the cache.
    """
    if cache_dir is None:
        return None
    cm = CacheManager(cache_dir)
    return cm.register_doc(source_path=input, to_cache=output, suffix=marker)


def mangle_allow_cached(data, default=True):
    """Pick ``allow_cached`` keyword from data.

    If the mentioned keyword is part of data dict, turn its string
    value unto bool (default as per `default` parameter) and
    return this value.
    """
    allow = string_to_bool(data.get('allow_cached', default))
    if 'allow_cached' in data.keys():
        # This is not data for processors
        del data['allow_cached']
    if allow is None:
        allow = default
    return allow


def get_cachedir(allow_cached, cache_dir, cache_layout, user):
    """Get a cachedir based on the given parameters.

    `allow_cached` is a boolean indicating, whether caching should be
    enabled. `cache_dir` is the path to a cache
    directory. `cache_layout` tells what kind of cache layout we want
    to use. Currenty we support :data:`CACHE_SINGLE` (share a single cache
    for all users) and :data:`CACHE_PER_USER` where each user gets an own
    part of cache. Both constants are importable from
    :mod:`ulif.openoffice.cachemanager`.

    Returns a path as string.
    """
    if cache_dir is None or not allow_cached:
        return None
    if cache_layout == CACHE_PER_USER:
        if user is None:
            return None
        cache_dir = os.path.join(cache_dir, user)
    return cache_dir


def process_doc(doc, data, cached_default, cache_dir, cache_layout, user):
    """Process `doc` according to the other parameters.

    `doc` is the path to the source document. `data` is a dict of
    options for processing, passed to the processors.

    Other parameters influence the caching behaviour: `cached_default`
    is a boolean indicating whether caching is allowed generally for
    this document. `cache_dir` gives the basic caching directory and
    `cache_layout` tells whether cached copies are stored in a shared
    cache (same docs for all users) or a 'private' cache. If we want a
    private cache, we have to pass `u.o.cachemanager.CACHE_PER_USER`
    and a username in `user`.

    Depending on the parameters we start by looking up a copy for the
    requested document conversion in the cache. If none is found (or
    caching forbidden/impossible) we generate a fresh conversion
    calling :class:`ulif.openoffice.processor.MetaProcessor` with
    `data` as parameters.

    Afterwards the conversion result is stored in cache (if
    allowed/possible) for speedup of upcoming requests.

    Returns a quadruple

      ``(<PATH>, <ETAG>, <METADATA>, <CACHED_COPY>)``

    where ``<PATH>`` is the path to the resulting document, ``<ETAG>``
    an identifier to retrieve a generated doc from cache on future
    requests, ``<METADATA>`` is a dict of values returned during
    request (and set by the document processors, notably setting the
    `error` keyword), and ``<CACHED_COPY>`` is a boolean indicating
    whether the result was retrieved from cache or generated.

    If retrieved from cache ``<ETAG>`` is normally
    ``None``. Same applies if errors happened or caching is forbidden.
    """
    result_path = None
    etag = None
    allow_cached = mangle_allow_cached(data, cached_default)
    allow_cached = allow_cached and cache_dir is not None
    marker = get_marker(data)  # Create unique marker out of options
    metadata = dict(error=False)
    if allow_cached and cache_dir is not None:
        # Ask cache for already stored copy
        real_cachedir = get_cachedir(
            allow_cached, cache_dir, cache_layout, user)
        result_path, etag = get_cached_doc(doc, marker, cache_dir=cache_dir)
        cached_result = True
    if result_path is None:
        # Generate result
        input_copy = None
        if allow_cached:
            input_copy = copy_to_secure_location(doc)
            input_copy = os.path.join(input_copy, os.path.basename(doc))
        proc = MetaProcessor(options=data)  # Removes original doc
        result_path, metadata = proc.process(doc)
        cached_result = False
        error_state = metadata.get('error', False)
        if allow_cached and not error_state and result_path is not None:
            # Cache away generated doc
            etag = cache_doc(input_copy, result_path, marker, cache_dir)
        if input_copy and os.path.isfile(input_copy):
            remove_file_dir(input_copy)
    return result_path, etag, metadata, cached_result


#
# Real server stuff
#


class DocumentRoot(object):
    exposed = True

    def __init__(self, cache_dir=None, cache_layout=CACHE_SINGLE):
        self.cache_dir = cache_dir
        self.cache_layout = cache_layout
        return

    def not_cp_dispatch(self, vpath):
        if vpath:
            doc_id = vpath.pop(0)
            if doc_id == 'index':
                return DocumentIndex(
                    cache_dir=self.cache_dir,
                    cache_layout=self.cache_layout)
            return Document(doc_id, cache_dir=self.cache_dir)
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
        result_path, etag, metadata, cached_result = process_doc(
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

        if etag is not None:
            # Set Etag header if we have one
            cherrypy.response.headers['Etag'] = '"%s"' % etag
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
            content += "<tr><td>%s</td><td>%s</td></tr>" % (
                name, proc.defaults)
        content += "</tbody></table>"
        content += "<h2>OpenOffice.org/LibreOffice Server:</h2>"
        content += "<table><thead><tr><th>key</th><th>value</th>"
        content += "</tr></thead><tbody>"
        content += '<tr><td>Status</td><td id="ooo_status">%s</td></tr>' % (
            check_port('localhost', 2002) and 'UP' or 'DOWN', )
        content += "</tbody></table>"
        content += "</body></html>"
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

userpassdict = {'bird': 'bebop', 'ornette': 'wayout'}
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
