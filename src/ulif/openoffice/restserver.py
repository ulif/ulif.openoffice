##
## restserver2.py
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
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.oooctl import check_port
from ulif.openoffice.processor import MetaProcessor
from ulif.openoffice.util import get_content_type
from ulif.openoffice.helpers import remove_file_dir, get_entry_points

class DocumentRoot(object):
    exposed = True

    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        return

    def not_cp_dispatch(self, vpath):
        if vpath:
            doc_id = vpath.pop(0)
            #cherrypy.request.params['doc_id'] = doc_id
            if doc_id == 'index':
                return DocumentIndex(cache_manager = self.cache_manager)
            return Document(doc_id, cache_manager=self.cache_manager)
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
        proc = MetaProcessor(options=data)
        result_path, metadata = proc.process(file_path)

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

    def __init__(self, cache_manager=None):
        self.ids = ids
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
        return DocumentRoot(cache_manager=self.cache_manager)

    status = Status()

    def __init__(self, cachedir=None):
        self.cache_manager = None
        if cachedir is None:
            return
        self.cache_manager = CacheManager(cachedir)
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
    (options, args) = parser.parse_args(argv[1:])

    from cherrypy.process.plugins import Daemonizer
    if options.daemonize is True:
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    cherrypy.quickstart(Root(), '/', options.config)
