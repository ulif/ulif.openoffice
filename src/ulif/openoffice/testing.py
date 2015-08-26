#
# testing.py
#
# Copyright (C) 2011, 2013, 2015 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
"""
Test helpers.
"""
import logging
import os
import shutil
import sys
import tempfile
import time
import unittest
import ulif.openoffice
from io import BytesIO, StringIO
from webob import Request
from ulif.openoffice.oooctl import check_port

try:
    from xmlrpc import client as xmlrpclib   # Python 3.x
except ImportError:                          # pragma: no cover
    import xmlrpclib                         # Python 2.x


class TestOOServerSetup(unittest.TestCase):
    """A setup that starts an OO.org server in background

    and shuts it down after tests in the accompanied test suite have
    been run.

    This setup is special in that it detects whether an instance of
    the openoffice server is already running and in that case uses
    this instance.

    For people running tests does that mean:

    - You can decrease test time (dramatically) by starting `oooctl`
      in backgroud before running tests.

    - An already running instance of OO.org server will be still
      running after tests.

    - Be prepared for slightly different test output when using an
      already running OO.org server instance.

    """
    @classmethod
    def setUpClass(cls):                                # pragma: no cover
        # Set clean HOME environment as OOO.org might scan it...
        cls._marker = object()
        cls.old_home = os.environ.get('HOME', cls._marker)
        cls.homedir = tempfile.mkdtemp()
        os.environ['HOME'] = cls.homedir

        # Don't start oooctl if it runs already...
        cls.ooo_running = False
        cls.oooctl_path = 'oooctl'

        if check_port('localhost', 2002):
            cls.ooo_running = True
            return

        # Start oooctl...
        cls.oooctl_path = 'oooctl'
        exe = sys.executable
        cls.oooctl_path = ulif.openoffice.oooctl.__file__
        cls.oooctl_path = os.path.splitext(cls.oooctl_path)[0] + '.py'
        cls.oooctl_path = '%s %s' % (exe, cls.oooctl_path)
        os.system(cls.oooctl_path + ' --stdout=/tmp/oooctl.log start')
        ts = time.time()
        while not check_port('localhost', 2002):
            time.sleep(0.5)
            if time.time() - ts > 3:
                break
            pass
        return

    @classmethod
    def tearDownClass(cls):                             # pragma: no cover
        # Only shut down oooctl if it were not running already...
        if cls.ooo_running is not True:
            os.system(cls.oooctl_path + ' stop')
            ts = time.time()
            while check_port('localhost', 2002):
                time.sleep(0.5)
                if time.time() - ts > 3:
                    break
                pass

        # Clean up dirs...
        shutil.rmtree(cls.homedir)

        # Set HOME to old state...
        if cls.old_home is cls._marker:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = cls.old_home
        return


def ls(dir, *subs):                                     # pragma: no cover
    if subs:
        dir = os.path.join(dir, *subs)
    names = os.listdir(dir)
    names.sort()
    for name in names:
        if os.path.isdir(os.path.join(dir, name)):
            print('d  ' + name)
        else:
            print('-  ' + name)
    return


def cat(dir, *names):                                   # pragma: no cover
    path = os.path.join(dir, *names)
    print(open(path).read())
    return


_old_cwd = os.getcwd()
_tmpdir = None


def doctest_setup():
    """Set up doctest env.

    Creates a temporary working dir and changes to it.

    Creates a 'document.doc' file in that directory.
    """
    _tmpdir = tempfile.mkdtemp()
    os.chdir(_tmpdir)
    open('document.doc', 'w').write('A simple testfile.')


def doctest_teardown():
    """Tear down doctest env.

    Removes any temporary working directory (if it is different from
    initial CWD).
    """
    global _old_cwd
    cwd = os.getcwd()
    if cwd != _old_cwd:
        os.chdir(_old_cwd)
        shutil.rmtree(cwd)


def doctest_rm_resultdir(path):
    """Remove directory `path`.

    If path is a file, the parent directory is removed.

    The directory is only removed, if it is not the current working
    directory.
    """
    path = os.path.abspath(path)
    if os.path.exists(path):
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if path == os.getcwd():                         # pragma: no cover
            return
        shutil.rmtree(path)


class TypeAwareStreamHandler(logging.StreamHandler):
    """A logging.StreamHandler that turns anything into 'unicode'.

    In tests we want to use StringIO buffers to read log messages (at
    least until we py.testified everything). As StringIO instances
    require unicode() instances under Python 2.x and str() instances
    under Python 3.x we do our best to convert anything before we emit
    messages. I.e. we decode any string to UTF-8 if possible (and let it
    pass as-is otherwise).
    """
    def emit(self, record):
        try:
            record.msg = record.msg.decode('utf-8')
        except AttributeError:
            # Python 3.x
            pass
        # XXX: Cannot use super() here, because in Python2.6 this
        # XXX: is an old-style class.
        return logging.StreamHandler.emit(self, record)


class ConvertLogCatcher(object):
    """This log catcher catches the log messages of u.o.convert().

    It must be instantiated before any call to u.o.convert.
    """

    def __init__(self):
        self.stream = StringIO()
        self.handler = TypeAwareStreamHandler(self.stream)
        self.logger = logging.getLogger('ulif.openoffice.convert')
        self.logger.setLevel(logging.DEBUG)
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        self.logger.addHandler(self.handler)

    def get_log_messages(self):
        self.handler.flush()
        result = self.stream.getvalue()
        self.handler.close()
        return result


class HTTPWSGIResponse(object):
    """A fake httplib-like HTTP response.

    Used by :class:`WSGILikeHTTP` for use by
    :class:`WSGIXMLRPCAppTransport`.

    .. versionadded:: 1.1
    """
    def __init__(self, webob_resp):
        self.resp = webob_resp
        self._body = BytesIO(self.resp.body)
        self._body.seek(0)
        self.reason = self.resp.status.split(" ", 1)
        self.status = self.resp.status_int

    def read(self, amt=None):
        return self._body.read()

    def getheader(self, name, default=None):
        return self.resp.headers.get(name, default)


class WSGILikeHTTP(object):
    """An httplib-like HTTP layer for WSGIXMLRPCAppTransport.

    .. versionadded:: 1.1
    """
    def __init__(self, host, app):
        self.app = app
        self.headers = {}
        self.content = BytesIO()

    def putrequest(self, method, handler, **kw):
        self.method = method
        self.handler = handler

    def putheader(self, key, value):
        self.headers[key] = value

    def endheaders(self, *args):
        if len(args):
            self.body = args[0]

    def send(self, body):                               # pragma: no cover
        # py2.6
        return self.endheaders(body)

    def getresponse(self, buffering=True):
        req = Request.blank(self.handler)
        for key, val in self.headers.items():
            req.headers[key] = val
        req.method = self.method
        req.body = self.body
        resp = req.get_response(self.app)
        self.content = BytesIO(resp.body)
        return HTTPWSGIResponse(resp)

    def getreply(self):                                 # pragma: no cover
        # py2.6
        resp = self.getresponse()
        return resp.status, resp.reason, resp.resp.headers

    def getfile(self):                                  # pragma: no cover
        # py2.6
        return self.content


class WSGIXMLRPCAppTransport(xmlrpclib.Transport):
    """A fake HTTP transport.

    The given `app` should be the XMLRPC WSGI app to serve. Usually a
    :class:`ulif.openoffice.xmlrpc.WSGIXMLRPCApplication` instance.

    Usable by xmlrpclib clients to fake connections to 'real' servers
    like :class:`xmlrpclib.SimpleXMLRPCServer` instances.

    With this transport you can create :class:`xmlrpclib.ServerProxy`
    instances that talk directly to the given `app` instead of doing
    real network requests.

    .. versionadded:: 1.1
    """
    def __init__(self, app):
        xmlrpclib.Transport.__init__(self)
        self.app = app

    def make_connection(self, host):
        host, extra_headers, x509 = self.get_host_info(host)
        return WSGILikeHTTP(host, self.app)


#: A WSGIXMLRPCApplication instance for use by :class:`FakeServerProxy`.
#: Set this var before creating a :class:`FakeServerProxy` instance
#: and the proxy will send requests to the set application.
xmlrcpapp = None


class FakeServerProxy(xmlrpclib.ServerProxy):
    """An :class:`xmlrpclib.ServerProxy` for doctests.

    Different to normal `ServerProxy` instances, this one uses a
    special transport to talk directly to the
    :class:`ulif.openoffice.xmlrpc.WSGIXMLRPCApplication` set in
    `xmlrpcapp`.

    .. versionadded:: 1.1
    """
    def __init__(self, url):
        transport = WSGIXMLRPCAppTransport(xmlrpcapp)
        xmlrpclib.ServerProxy.__init__(self, url, transport=transport)
