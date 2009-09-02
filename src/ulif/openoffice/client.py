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


class PyUNOServerClient(object):
    """A basic client to communicate with a running pyunoserver.
    """

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    def send_request(self, message):
        (ip, port) = self.ip, self.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        f = sock.makefile('r', 0)
        f.write(message)
        response = f.readlines()
        sock.close()
        return ''.join(response)
