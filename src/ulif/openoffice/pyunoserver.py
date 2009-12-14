##
## pyunoserver.py
## Login : <uli@pu.smp.net>
## Started on  Fri Aug 28 02:13:03 2009 Uli Fouquet
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
"""A server that waits for requests for conversion of documents.

Important code fragments are from regular Python documentation.
"""
import os
import socket
import sys
import threading
import SocketServer
from urlparse import urlsplit
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.convert import convert_to_pdf, convert

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        """The protocol:

        The request:
        <REQUEST> := <CONVERT_CMD>|<TEST_CMD>
        <CONVERT-CMD> := <CMD><PATH>
        <CMD> := "CONVERT_PDF\n"|"CONVERT_HTML\n"
        <TEST_CMD> := "TEST\n"
        <PATH> := "PATH="<PATH-TO-DOCUMENT>"\n"
        <PATH-TO-DOCUMENT> := file-path

        Response:
        <OK-RESULT>|<ERR-RESULT>|<VERSION-RESULT>
        with:
        <OK-RESULT> := "OK "<STATUS>" "<PATH-TO-RESULT>
        <ERR-RESULT> := "ERR "<STATUS>" "<ERR-MSG>
        <STATUS> := a number (?)
        <PATH-TO-RESULT> := file-path
        <ERR-MSG> := text (possibly several lines)
        <VERSION-RESULT> := "OK 0 "server-version

        Examples:
        Request:
          CONVERT_PDF
          PATH=/home/foo/bar.odt
        Response:
          OK 0 /tmp/asdqwe.pdf

        Request:
          CONVERT_HTML
          PATH=/home/foo/bar.docx
        Response:
          OK 0 /tmp/sdfwqer
        
        Request:
          TEST
        Response:
          ERR -1 Could not reach OpenOffice.org server on port 2002
          Please make sure to start oooctl.

        """
        data = self.rfile.readline().strip()
        if "TEST" == data:
            self.wfile.write('OK 0 0.1dev\n')
            return
        if data not in ["CONVERT_PDF", "CONVERT_HTML"]:
            self.wfile.write('ERR 550 unknown command. Use CONVERT_HTML, '
                             'CONVERT_PDF or TEST.\n')
            return
        key, path = self.getKeyValue(self.rfile.readline())
        if key is None or key != "PATH":
            self.wfile.write('ERR 550 missing path.')
            return
        
        if data == 'CONVERT_PDF':
            self.wfile.write('path: %s\n' % path)
            filter_name = "writer_pdf_Export"
            extension  = "pdf"
        if data == 'CONVERT_HTML':
            self.wfile.write('path: %s\n' % path)
            filter_name = "HTML (StarWriter)"
            extension  = "html"

        # Ask cache before doing conversion...
        cm = self.server.cache_manager
        dest_path = cm.getCachedDocPath(path, ext=extension)
        if dest_path is not None:
            self.wfile.write('OK 200 %s' % (dest_path,))
            return
            
        ret_val = -1
        dest_path = ''
        try:
            (ret_val, dest_paths) = convert(
                filter_name=filter_name, extension=extension, paths=[path])
            if len(dest_paths):
                dest_path = urlsplit(dest_paths[0])[2]
        except Exception, e:
            self.wfile.write('ERR 550 %s: %s\n' % (e.__class__, e.message) )
            return
        except:
            self.wfile.write('ERR 550 internal pyuno error \n')
        if ret_val != 0:
            self.wfile.write('ERR 550 conversion not finished: %s' % (
                    ret_val,))
        else:
            # Notify cache manager...
            cm.registerDoc(source_path=path, to_cache=dest_path)
            self.wfile.write('OK 200 %s' % (dest_path,))
        return

    def getKeyValue(self, line):
        if "=" not in line:
            return (None, None)
        key, value = line.split('=', 1)
        return (key.strip(), value.strip())


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """An asynchronous TCP server.
    """

    cache_manager = None
    
    def server_bind(self):
        # We use SO_REUSEADDR to ensure, that we can reuse the port on
        # restarts immediately. Otherwise we would be blocked by
        # TIME_WAIT for several seconds or minutes.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return SocketServer.TCPServer.server_bind(self)

    
def run(host, port, python_binary, uno_lib_dir, cache_dir):
    print "START PYUNO DAEMON"
    # Port 0 means to select an arbitrary unused port
    #HOST, PORT = host, port"localhost", 2009

    cache_manager = CacheManager(cache_dir)
    
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    server.cache_manager = cache_manager

    # This will run until shutdown without consuming CPU cycles all
    # the time...
    server.serve_forever()
