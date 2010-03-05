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
import pkg_resources
import shutil
import signal
import socket
import sys
import tarfile
import tempfile
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
        logger = self.server.logger
        data = self.rfile.readline().strip()
        if "TEST" == data:
            info = pkg_resources.get_distribution('ulif.openoffice')
            self.wfile.write('OK 0 %s\n' % info.version)
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
        dest_path = cm.getCachedFile(path, suffix=extension)
        if dest_path is not None:
            # TODO: Here we might unpack stuff, copy to secure location etc.
            dest_path = self.prepareCacheResults(path, dest_path, extension)
            self.wfile.write('OK 200 %s' % (dest_path,))
            return
            
        ret_val = -1
        dest_path = ''
        # Copy source to safe destination...
        path = self.prepareSource(path, extension)
        path_dir = os.path.dirname(path)
        try:
            (ret_val, dest_paths) = convert(
                filter_name=filter_name, extension=extension, paths=[path])
            if len(dest_paths):
                dest_path = urlsplit(dest_paths[0])[2]
        except Exception, e:
            self.wfile.write('ERR 550 %s: %s\n' % (e.__class__, e.message) )
            shutil.rmtree(path_dir)
            return
        except:
            self.wfile.write('ERR 550 internal pyuno error \n')
        if ret_val != 0:
            self.wfile.write('ERR 550 conversion not finished: %s' % (
                    ret_val,))
            shutil.rmtree(path_dir)
        else:
            # Notify cache manager...
            cache_path = self.prepareCaching(path, dest_path, extension)
            cm.registerDoc(source_path=path, to_cache=cache_path,
                           suffix=extension)
            # Remove source and tarfile from result...
            if cache_path != dest_path:
                os.unlink(cache_path)
            os.unlink(path)
            
            self.wfile.write('OK 200 %s' % (dest_path,))
        return

    def prepareSource(self, src_path, extension):
        """We move the source to a secure location.

        This way we prevent results from being polluted by already
        existing files not belonging to the result.
        """
        new_dir = tempfile.mkdtemp()
        basename = os.path.basename(src_path)
        safe_src_path = os.path.join(new_dir, basename)
        shutil.copy2(src_path, safe_src_path)
        return safe_src_path

    def prepareCaching(self, src_path, result_path, extension):
        """Before we can feed the cachemanager, we tar HTML results.
        """
        if extension == 'html':
            basename = os.path.basename(result_path)
            dirname = os.path.dirname(result_path)
            tarname = basename + '.tar.gz'
            result_path = os.path.join(dirname, tarname)
            # Temporarily move source out of result dir...
            fd, tmpfile = tempfile.mkstemp()
            shutil.move(src_path, tmpfile)
            # Create tarfile out of result dir...
            tfile = tarfile.open(name=result_path, mode="w:gz")
            tfile.add(dirname, 'result')
            tfile.close()
            # Move source back into result dir...
            shutil.move(tmpfile, src_path)
        return result_path
    
    def prepareCacheResults(self, src_path, result_path, extension):
        """Move results to a secure destination.

        If the result is HTML we try to untar the result file.
        """
        # copy results to safe location...
        new_dir = tempfile.mkdtemp()
        result_base = os.path.splitext(os.path.basename(src_path))[0]
        safe_result_path = os.path.join(new_dir, '%s.%s' % (
                result_base, extension))
        # HTML results must be untarred...
        if extension == 'html':
            tar = tarfile.open(result_path, 'r:gz')
            for tarinfo in tar:
                tar.extract(tarinfo, new_dir)
            tar.close()
            # move files from result to upper dir...
            resultdir = os.path.join(new_dir, 'result')
            for filename in os.listdir(resultdir):
                src = os.path.join(resultdir, filename)
                dest = os.path.join(new_dir, filename)
                if filename.endswith('html'):
                    # Make sure that blah.doc results in blah.html
                    # even if it comes from cache and the original doc
                    # was named foo.doc (generating foo.html)
                    dest = safe_result_path
                shutil.copy2(src, dest)
            shutil.rmtree(resultdir)
        else:
            shutil.copy2(result_path, safe_result_path)            
        return safe_result_path

    def getKeyValue(self, line):
        if "=" not in line:
            return (None, None)
        key, value = line.split('=', 1)
        return (key.strip(), value.strip())


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """An asynchronous TCP server.
    """

    cache_manager = None
    logger = None
    do_stop = False
    
    def server_bind(self):
        # We use SO_REUSEADDR to ensure, that we can reuse the port on
        # restarts immediately. Otherwise we would be blocked by
        # TIME_WAIT for several seconds or minutes.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return SocketServer.TCPServer.server_bind(self)

    def serve_forever(self):
        while not self.do_stop:
            self.handle_request()

    def shutdown(self):
        self.do_stop = True


def run(host, port, python_binary, uno_lib_dir, cache_dir, logger):
    #print "START PYUNO DAEMON"
    # Port 0 means to select an arbitrary unused port
    #HOST, PORT = host, port"localhost", 2009

    cache_manager = CacheManager(cache_dir)
    
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    server.cache_manager = cache_manager
    server.logger = logger

    def signal_handler(signal, frame):
        print "Received SIGINT."
        print "Stopping PyUNO server."
        server.shutdown()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    
    # This will run until shutdown without consuming CPU cycles all
    # the time...
    server.serve_forever()
