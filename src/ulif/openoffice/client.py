##
## client.py
## Login : <uli@pu.smp.net>
## Started on  Wed Sep  2 16:50:35 2009 Uli Fouquet
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
"""Client components for communications with pyunoservers.

This way we can better make sure to have a solid interface for
third-party software.
"""
import socket
from ulif.openoffice.pyunoctl import PORT as PYUNO_PORT


class PyUNOResponse(object):

    def __init__(self, rawresponse):
        isok, status, msg = self.processRawResponse(rawresponse)
        self.ok = isok
        self.status = status
        self.message = msg

    def processRawResponse(self, response):
        isok = False
        status = 550
        if response is None or len(response) == 0:
            return (False, 550, '')
        if '\n' in response:
            lines = response.split('\n')
            if len(lines[-1]) > 0:
                response = lines[-1]
            elif len(lines) > 1 and len(lines[-2]) > 0:
                response = lines[-2]
            else:
                return (False, 550, '')
        else:
            return (False, 550, '')
        response = response.strip()
        parts = response.split(' ', 2)
        try:
            status = int(parts[1])
        except:
            return (False, 550, '')
        if parts[0] == 'OK':
            isok = True
        message = parts[2]
        return (isok, status, message)
        

class PyUNOServerClient(object):
    """A basic client to communicate with a running pyunoserver.
    """
    
    def __init__(self, ip='127.0.0.1', port=PYUNO_PORT):
        self.ip = ip
        self.port = port
    
    def sendRequest(self, message):
        (ip, port) = self.ip, self.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        f = sock.makefile('r', 0)
        f.write(message)
        response = f.readlines()
        sock.close()
        return PyUNOResponse(''.join(response))
