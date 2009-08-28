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
import sys
import socket
import threading
import SocketServer

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
            self.wfile.write('ERR -1 unknown command. Use CONVERT_HTML, '
                             'CONVERT_PDF or TEST.\n')
            return
        key, path = self.getKeyValue(self.rfile.readline())
        if key is None or key != "PATH":
            self.wfile.write('ERR -1 missing path.')
            return
        self.wfile.write('OK convert %s' % path)
        return

    def getKeyValue(self, line):
        if "=" not in line:
            return (None, None)
        key, value = line.split('=', 1)
        return (key.strip(), value.strip())


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """An asynchronous TCP server.
    """
    def server_bind(self):
        # We use SO_REUSEADDR to ensure, that we can reuse the port on
        # restarts immediately. Otherwise we would be blocked by
        # TIME_WAIT for several seconds or minutes.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return SocketServer.TCPServer.server_bind(self)


def run(host, port, python_binary, uno_lib_dir):
    print "START PYUNO DAEMON"
    # Port 0 means to select an arbitrary unused port
    #HOST, PORT = host, port"localhost", 2009

    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    #server.allow_reuse_address = reuse_port
    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.setDaemon(True)
    server_thread.start()
    print "Server loop running in thread:", server_thread.getName()
    
    while 1:
        # Run (nearly) forever...
        pass
