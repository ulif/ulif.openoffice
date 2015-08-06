#
# xmlrpc.py
#
# Copyright (C) 2013, 2015 Uli Fouquet
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
Components to convert documents via XML-RPC.

.. versionadded:: 1.1

"""
from webob import Response, exc
from webob.dec import wsgify
from ulif.openoffice.client import Client, convert_doc
try:
    from SimpleXMLRPCServer import SimpleXMLRPCDispatcher  # Python 2.x
except ImportError:                                        # pragma: no cover
    from xmlrpc.server import SimpleXMLRPCDispatcher       # Python 3.x


class WSGIXMLRPCApplication(object):
    """WSGI application to handle requests to the XMLRPC service.

    This WSGI application acts like the Python standard
    `SimpleXMLRPCServer` but processes WSGI requests instead and does
    not fiddle around with raw HTTP.

    The passed in `cache_dir` is used only if set.
    """
    def __init__(self, cache_dir=None):
        # set up a dispatcher
        self.dispatcher = SimpleXMLRPCDispatcher(
            allow_none=True, encoding=None)
        self.dispatcher.register_function(
            self.convert_locally, 'convert_locally')
        self.dispatcher.register_function(
            self.get_cached, 'get_cached')
        self.dispatcher.register_introspection_functions()
        self.cache_dir = cache_dir

    def convert_locally(self, src_path, options):
        """Convert document in `path`.

        Expects a local path to the document to convert.

        The `options` are a dictionary of options as accepted by all
        converter components in this package.

        The cache (if set) will be updated.

        Returns path of converted document, a cache key and a
        dictionary of metadata. The cache key is ``None`` if no cache
        was used.
        """
        result_path, cache_key, metadata = convert_doc(
            src_path, options, self.cache_dir)
        return result_path, cache_key, metadata

    def get_cached(self, cache_key):
        """Get a cached document.

        Retrieve the document representation stored under `cache_key`
        in cache if it exists. Returns `None` otherwise.
        """
        client = Client(cache_dir=self.cache_dir)
        return client.get_cached(cache_key)

    @wsgify
    def __call__(self, req):
        """Handles the HTTP POST request.

        Attempts to interpret all HTTP POST requests as XML-RPC calls,
        which are forwarded to the server's _dispatch method for
        handling.

        Most code taken from SimpleXMLRPCServer with modifications for
        wsgi and my custom dispatcher.
        """
        if req.method != 'POST':
            return exc.HTTPBadRequest()
        try:
            data = req.environ['wsgi.input'].read(req.content_length)
            response = self.dispatcher._marshaled_dispatch(
                data, self.dispatcher._dispatch
            ) + '\n'
        except:                                         # pragma: no cover
            # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            return exc.HTTPServerError()
        else:
            # got a valid XML RPC response
            response = Response(response)
            response.content_type = 'text/xml'
            return response


def make_xmlrpc_app(global_conf, **local_conf):
    return WSGIXMLRPCApplication(**local_conf)
