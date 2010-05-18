##
## restserver.py
## Login : <uli@pu.smp.net>
## Started on  Tue Oct 27 12:03:38 2009 Uli Fouquet
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
"""A conversion server using REST.

   This server is not in a usable state yet.
"""
import cgi
import os
import pkg_resources
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlsplit
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.convert import convert_to_pdf, convert

class PyUNORestHandler(BaseHTTPRequestHandler):
    def do_GET(self, *args, **kw):
        """Handle requests to existing documents.
        """
        path = self.path.split('/')[1:]
        if len(path) == 1 and path[0] == 'TEST':
            self.sendTestReply()
            return
        if len(path) > 1:
            md5digest = path[0]
            ext = path[1].lower()
            cm = self.server.cache_manager
            dir = cm.getCacheDir(ext, md5digest)
            if os.path.exists(dir):
                self.sendMessage('OK\n')
                return
        self.send_error(404, 'File Not Found: %s' % self.path)

    def do_POST(self):
        # Parse the form data posted
        ctype =  self.headers.getheader('content-type')
        if not ctype.startswith('multipart/form-data'):
            # We currently require multipart/form-data...
            self.send_error(406)
            return
        print "POST OK"
        form = cgi.FieldStorage(
            fp=self.rfile, 
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })

        # Begin the response
        self.send_response(200)
        self.end_headers()
        self.wfile.write('Client: %s\n' % str(self.client_address))
        self.wfile.write('Path: %s\n' % self.path)
        self.wfile.write('Form data:\n')
        #return

        # Echo back information about what was posted in the form
        for field in form.keys():
            field_item = form[field]
            if field_item.filename:
                #if field_item.filename:
                # The field contains an uploaded file
                file_data = field_item.file.read()
                file_len = len(file_data)
                del file_data
                self.wfile.write('\tUploaded %s (name=%s; %d bytes)\n' % (
                        field, field_item.filename, file_len))
            else:
                # Regular form value
                self.wfile.write('\t%s=%s\n' % (field, form[field].value))
        return
        
    def sendTestReply(self):
        version = pkg_resources.get_distribution('ulif.openoffice').version
        response = "ulif.openoffice.RESTful.HTTPServer %s\n" % version
        self.sendMessage(response)
        return

    def sendMessage(self, message):
        self.send_response(200)
        self.send_header('Content-Length:', str(len(message)))
        self.end_headers()
        self.wfile.write(message)
        
def run(host, port, python_binary, uno_lib_dir, cache_dir, logger):
    server_address = (host, port)
    cache_manager = CacheManager(cache_dir)
    httpd = HTTPServer(server_address, PyUNORestHandler)
    httpd.cache_manager = cache_manager
    httpd.logger = logger
    httpd.serve_forever()

if __name__ == '__main__':
    run('localhost', 8000, None, None, '/home/uli/.pyunocache')
