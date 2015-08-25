Converting Docs via HTTP
========================

.. testsetup::

    >>> import os
    >>> import shutil
    >>> import tempfile
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
    >>> getfixture("envpath_no_venv")

The included WSGI app provides access to `unoconv`_ and filters in this
package via HTTP. More specificially we provide a RESTful_ WSGI_ app
that can be served by HTTP servers and optionally caches result docs.


Setting Up the WSGI App With Paste
----------------------------------

To run the included RESTful doc converter WSGI_ app we can use
`Paste`_. The required `paster` script can be installed locally with::

  (py27) pip install PasteScript

Then we need a `PasteDeploy`_ compatible config file like the following
``sample.ini``::

  # sample.ini
  # A sample config to run WSGI components with paster
  [app:main]
  use = egg:ulif.openoffice#docconverter
  cache_dir = /tmp/mycache

  [server:main]
  use = egg:Paste#http
  host = localhost
  port = 8008

In the ``[app:main]`` section we tell to serve the `ulif.openoffice`
WSGI app `docconverter`. We additionally set a directory where we
allow cached documents to be stored. This entry (``cache_dir``) is
optional. Just leave it out if you do not want caching of result docs.

The ``[server:main]`` section simply tells to start an HTTP server on
localhost port 8008. ``host`` can be set to any local hostname or an
IP number. Set it to ``0.0.0.0`` to be accessible on all IPs assigned
to the current machine (but read the security infos below, first!).

You now can start a conversion server::

  (py27) $ paster serve sample.ini

and start converting real office documents via HTTP on the configured
host and port (here: localhost:8008).

While we use the `Paste`_ HTTP server here for demonstration, you are
not bound to this choice. Of course you can use any HTTP server
capable of serving WSGI apps you like. This includes at least `Apache`
and `nginx` (with appropriate modules loaded).


.. _securing_wsgi:

Securing the Document Converter (optional)
------------------------------------------

As told above, you can set the listening port of the Paste_ HTTP
server to ``0.0.0.0`` which will make it accessible for everyone and
from everywhere (given you're not protected by local firewalls,
etc.). This might not be what you want.

Therefore with `ulif.openoffice` we provide simple authentication
(another WSGI_ app) that requires HTTP basic auth authentication for
incoming requests and checks sent credentials against a local
``htaccess``-like file.

To activate it, you can create a ``sample.ini`` like this::

  # An sample config to run WSGI components with paster
  [app:main]
  use = egg:ulif.openoffice#docconverter
  filter-with = auth_htaccess
  cache_dir = /tmp/mycache

  [server:main]
  use = egg:Paste#http
  host = localhost
  port = 8008

  [filter:auth_htaccess]
  use = egg:ulif.openoffice#htaccess
  realm = Sample Realm
  htaccess =  %(here)s/htaccess
  # possible values: plain, sha1, crypt
  auth_type = plain

This setup is basically the same as the one above, but with an
additional ``auth_htaccess`` filter injected that is configured in the
``[filter:auth_htaccess]`` section.

The ``htaccess`` filter requires three options:

`realm` - The authentication realm.
    Some text. Might be shown by webbrowsers when asking the user for
    credentials in the basic-auth dialog (normally some popup).

`htaccess` - The path to some password file.
    Here we set the path to some file called ``htaccess`` in the local
    directory.

`auth_type` - The encryption type of passwords in the password file.
    Possible values are ``plain`` (clear text passwords), ``sha1``, or
    ``crypt`` for the respective encryption types. Different to
    regular Apache htaccess files, ``md5`` is *not* supported. All
    passwords in the chosen password file are expected to be encrypted
    with the encryption type set here. You cannot mix-up plain, crypt,
    and SHA1 encrypted passwords.

The password file set by the `htaccess` option can be some regular
Apache htaccess file (given you avoid ``md5`` encryption). It can even
be edited using the `htpasswd` commandline tool (if installed).

A typical plain text password file could look like this::

  # htaccess
  # A password file for the document converter.
  # Supported encryption types: plain, crypt, sha1
  # Not supported: md5
  # You can use htpasswd to edit me.
  # All passwords must have same encryption type.
  bird:bebop
  ornette:wayout

would allow user ``bird`` access when authenticating with plain
password ``bebop``. With this setup anonymous doc conversions are not
possible.

Of course you can pick a different WSGI filter to protect your
document conversion server, but this one is already included in
`ulif.openoffice` and might serve for simple use-cases.


Converting Documents
--------------------

Once the server runs, we can start converting docs via HTTP.

The `ulif.openoffice` WSGI app supports the following HTTP-based
protocol to create, update, and remove documents:

============= =============== ============= ===============================
 HTTP method      Path           Params            Semantics
============= =============== ============= ===============================
 GET           /docs/new       `none`        Get an HTML form to trigger a
                                             new conversion.
------------- --------------- ------------- -------------------------------
 POST          /docs           doc,          Create a new conversion.
                               [other...]
------------- --------------- ------------- -------------------------------
 GET           /docs/<docid>   `none`        Get a cached conversion.
============= =============== ============= ===============================

Currently, removal and updating are not supported.


Creating New Resources
----------------------

Via ``GET`` to ``/docs/new`` you can get an HTML form usable in a
browser to send new documents to the server. This form provides a
very limited set of options you can set for the conversion.

    >>> url = 'http://localhost/docs/new'
    >>> print(browser.GET(url))          # doctest: +NORMALIZE_WHITESPACE
    200 OK
    Content-Type: text/html; charset=UTF-8
    Content-Length: ...
    <BLANKLINE>
    <html>
      <head>
        <title>Create a new doc</title>
      </head>
      <body>
        <form method="POST" action="/docs"
              enctype="multipart/form-data">
        ...
        </form>
      </body>
    </html>
    <BLANKLINE>

Via a ``POST`` to ``/docs`` you can send a document to the server that
will be converted. The result will be the converted document.

    >>> url = 'http://localhost/docs'
    >>> form = {'doc': ('sample.txt', 'Some Content'),
    ...         'oocp-out-fmt': 'html'}
    >>> response = browser.POST(url, **form)
    >>> response.status
    '201 Created'

    >>> for key in sorted(response.headers.keys()):
    ...     print("%s: %s" % (key, response.headers.get(key)))
    Content-Length: ...
    Content-Type: application/zip
    ETag: "...-...-..."
    Last-Modified: ...
    Location: http://localhost:80/docs/78138d2003f1a87043d65c692fb3a64b_1_1

    >>> response.body.startswith(b"PK")
    True

Here we converted a `sample.txt` file to HTML. To do that we POSTed a
request to the server with two parameters:

`doc`
   the file to be converted.

`oocp-out-fmt`
   the output format we want the document to be converted to.

While the `doc` parameter is mandatory, other parameters are
optional. The `oocp-out-fmt` parameter, for instance, is set to
``html`` by default and you don't have to send it with the
request. See :mod:`ulif.openoffice.processor` for the options of
different document processors.

With the response we not only get the converted document (packed into
a ZIP file), but also some helpful information:

Stating ``201 Created`` the server indicates that the converted
document was cached after creation and can be retrieved in future from
the URI given in the ``Location`` header.

.. note:: The cached location for later retrieval of the generated
          document works only, if caching is enabled for the REST
          server. If it is not, you will get status ``200 OK`` and no
          ``Location`` header instead.

To get a complete list of supported document processing options you
can run::

  (py27) $ oooclient --help

The WSGI document converter accepts all short options (the ones with a
leading single dash) with the leading dash removed. For example while
``oooclient`` accepts

  ``-oocp-out-fmt`` and ``--oocp-output-format``,

the WSGI app accepts only

  ``oocp-out-fmt``

without the leading dash. The same applies to all other options listed
by ``oooclient --help``.



.. testcleanup::

    >>> os.chdir(_old_root)
    >>> shutil.rmtree(_root)

.. _unoconv: https://github.com/dagwieers/unoconv
.. _RESTful: http://en.wikipedia.org/wiki/Representational_state_transfer
.. _WSGI: http://www.wsgi.org/
.. _Paste: http://pythonpaste.org/
.. _PasteScript: https://pypi.python.org/pypi/PasteScript
.. _PasteDeploy: https://pypi.python.org/pypi/PasteDeploy
