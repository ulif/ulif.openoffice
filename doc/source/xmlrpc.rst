Converting Docs via XMLRPC
==========================

.. testsetup::

    >>> import os
    >>> import shutil
    >>> import tempfile
    >>> from pprint import pprint
    >>> from webob import Request
    >>> from ulif.openoffice.testing import ls, cat
    >>> from ulif.openoffice.wsgi import RESTfulDocConverter
    >>> _root = tempfile.mkdtemp()
    >>> _cachedir = os.path.join(_root, 'cache')
    >>> _home = os.path.join(_root, 'home')
    >>> workdir = _home
    >>> _old_root = os.getcwd()
    >>> os.mkdir(_home)
    >>> os.chdir(_root)
    >>> app = RESTfulDocConverter(cache_dir=_cachedir)
    >>> class Browser(object):
    ...   app = app
    ...   def GET(self, url):
    ...     req = Request.blank(url)
    ...     return app(req)
    ...   def POST(self, url, **kw):
    ...     req = Request.blank(url, POST=kw)
    ...     return app(req)
    >>> browser = Browser()

    >>> from ulif.openoffice.xmlrpc import WSGIXMLRPCApplication
    >>> from ulif.openoffice import testing as xmlrpclib
    >>> app = WSGIXMLRPCApplication(cache_dir=_cachedir)
    >>> xmlrpclib.xmlrpcapp = app
    >>> from ulif.openoffice.testing import FakeServerProxy as ServerProxy

One of the included WSGI apps provides access to `unoconv`_ and
filters in this package via XMLRPC_. More specificially we provide a
WSGI_ app that can be served by HTTP servers and will then talk to
XMLRPC_ clients, optionally caching result docs.


Setting Up the XMLRPC_ App With Paste
-------------------------------------

To run the included XMLRPC_ doc converter WSGI_ app we can use
`Paste`_. The required `paster` script can be installed locally with::

  (py27) pip install PasteScript

Then we need a `PasteDeploy`_ compatible config file like the following
``xmlrpc.ini``::

  # xmlrpc.ini
  # A sample config to run WSGI XMLRPC app with paster
  [app:main]
  use = egg:ulif.openoffice#xmlrpcapp
  cache_dir = /tmp/mycache

  [server:main]
  use = egg:Paste#http
  host = localhost
  port = 8008

In the ``[app:main]`` section we tell to serve the `ulif.openoffice`
WSGI app `xmlrpcapp`. We additionally set a directory where we
allow cached documents to be stored. This entry (``cache_dir``) is
optional. Just leave it out if you do not want caching of result docs.

The ``[server:main]`` section simply tells to start an HTTP server on
localhost port 8008. ``host`` can be set to any local hostname or an
IP number. Set it to ``0.0.0.0`` to be accessible on all IPs assigned
to the current machine (but read the security infos below, first!).

You now can start an XMLRPC_ conversion server::

  (py27) $ paster serve xmlrpc.ini

and start converting real office documents via XMLRPC_ on the
configured host and port (here: localhost:8008).

While we use the `Paste`_ HTTP server here for demonstration, you are
not bound to this choice. Of course you can use any HTTP server
capable of serving WSGI apps you like. This includes at least `Apache`
and `nginx` (with appropriate modules loaded).


Securing the XMLRPC_ app (optional)
-----------------------------------

For the `ulif.openoffice` XMLRPC_ app applies the same as for the
RESTful document converter in this regard. See :ref:`securing_wsgi`
for details.


Converting Documents via XMLRPC_
--------------------------------

Once the server is running, we can start converting docs via XMLRPC_.
With standard Python :py:mod:`xmlrpclib` this is very easy:

    >>> server = ServerProxy('http://localhost:8008')

The `ServerProxy` can be imported from :py:mod:`xmlrpclib` (Python
2.x) or from `xmlrpc.client` (Python 3.x).

The `ulif.openoffice` XML-RPC server provides the following methods:

    >>> server.system.listMethods()     # doctest: +NORMALIZE_WHITESPACE
    ['convert_locally', 'get_cached', 'system.listMethods',
     'system.methodHelp', 'system.methodSignature']

If the server is running on the same machine as the client, i.e. both
components can access the same filesystem, then `convert_locally()` is
the fastest method to convert documents via XMLRPC_.

`convert_locally` takes as arguments a path to a source document and a
dictionary of options:

    >>> open('sample.txt', 'w').write('Some Content')
    >>> result = server.convert_locally('sample.txt', {})
    >>> pprint(result)              # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
    ['/.../sample.html.zip',
     '78138d2003f1a87043d65c692fb3a64b_1_1',
     {'error': False, 'oocp_status': 0}]

The result consists of a result path, a cache key and a dict with
metadata: ``(<PATH>, <CACHE_KEY>, <METADATA>)``.

The result path will be in a newly created directory.

.. note:: It is up to you to remove the result directory after usage.

Here the result is a ZIP file that includes any CSS stylesheets,
images, etc. generated. You can retrieve an non-zipped version by
setting options to something like:

    ``{'oocp-out-fmt': 'html', 'meta-procord': 'oocp'}``

which tells the converter to run only the core converter (no post
processing, etc.) and to generate HTML output.

The cache key is ``None`` if the XMLRPC server were configured without
a cache. This can be modified in ``xmlrpc.ini``.

The metadata dict contains especially infos about errors happened
during processing. You can normally ignore it, as failed conversions
will be signalled by an :class:`xmlrpclib.Fault` result.

.. doctest::
   :hide:

    >>> shutil.rmtree(os.path.dirname(result[0]))  # clean up

To produce different results, you can pass in different options
dict. In the example above we simply used the default (an empty dict),
but we can also produce a PDF file:

    >>> options = {'oocp-out-fmt': 'pdf', 'meta-procord': 'oocp'}
    >>> result = server.convert_locally('sample.txt', options)
    >>> pprint(result)             # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
    ['/.../sample.pdf',
     '78138d2003f1a87043d65c692fb3a64b_1_2',
     {'error': False, 'oocp_status': 0}]

Here we used the options ``oocp-out-fmt`` and ``meta-procord``. The
first one tells LibreOffice to produce PDF output and the latter
option tells to call only the ``oocp`` processor.

See :mod:`ulif.openoffice.processor` for the names and options of
different document processors. You can also run the commandline client::

  (py27) $ oooclient --help

to get a list of all supported options. Please note, that option keys
must be provided without leading dash.

.. doctest::
   :hide:

    >>> shutil.rmtree(os.path.dirname(result[0]))  # clean up

Retrieving Cached Docs via XMLRPC_
----------------------------------

Beside converting new docs we can also retrieve already cached docs
via XMLRPC_ using the `get_cached()` method. For this we need the
cache key provided in a conversion result.

    >>> result = server.get_cached('78138d2003f1a87043d65c692fb3a64b_1_2')
    >>> result                      # doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
    '/.../sample.pdf'

Of course this works only, if the XMLRPC server runs on the same
machine as the client but the operation is pretty fast compared to
converting.

.. note:: The result path is located *inside* the cache! The result
          file is therefore part of the cache and should not be
          modified! Instead please copy the file to an outside cache
          location or your cache will get corrupted.

.. testcleanup::

    >>> os.chdir(_old_root)
    >>> shutil.rmtree(_root)

.. _unoconv: https://github.com/dagwieers/unoconv
.. _XMLRPC: http://en.wikipedia.org/wiki/XML-RPC
.. _WSGI: http://www.wsgi.org/
.. _Paste: http://pythonpaste.org/
.. _PasteScript: https://pypi.python.org/pypi/PasteScript
.. _PasteDeploy: https://pypi.python.org/pypi/PasteDeploy
