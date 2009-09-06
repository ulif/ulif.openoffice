Detailed Description
********************

.. contents::


``oooctl`` -- the OOo daemon
============================

We can start an OpenOffice.org daemon using the `oooctl` script. This
daemon starts an already installed OpenOffice.org instance as server
(without GUI, so it is usable on servers).

The `oooctl` script is defined in `setup.py` to be installed as a
console script, so if you install `ulif.openoffice` with
`easy_install` or `setup.py`, an executable script will be installed
in your local `bin/` directory.

Here we 'fake' this install by using buildout, which will install the
script in our test environment.

To do so we create a `buildout.cfg` file:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = openoffice-ctl
    ... offline = true
    ...
    ... [openoffice-ctl]
    ... recipe = zc.recipe.egg
    ... eggs = ulif.openoffice
    ... ''')

Now we can run buildout to install our script (and other scripts,
described below, as well):

    >>> print system(join('bin', 'buildout'))
    Installing openoffice-ctl.
    Generated script '.../bin/pyunoctl'.
    Generated script '.../bin/convert'.
    Generated script '.../bin/oooctl'.
    <BLANKLINE>

The script provides help with the ``-h`` switch:

    >>> print system(join('bin', 'oooctl') + ' -h')
    Usage: oooctl [options] start|stop|restart|status
    ...

The main actions are to call the script with one of the::

  start|stop|restart|status

commands as argument.

We set the `oooctl` path as a var for further use:

    >>> oooctl_bin = join('bin', 'oooctl')


**-b** -- Setting the OpenOffice.org installation path
------------------------------------------------------

`oooctl` needs to know, which OOo install should be used and where it
lives. We can set this path to the binary using the ``-b`` or
``--binarypath`` switch of `oooctl`.

By default this path is set to:

    >>> from ulif.openoffice.oooctl import OOO_BINARY
    >>> OOO_BINARY
    '/usr/lib/openoffice/program/soffice'

which might not be true for your local system.

For our local test we create an executable script which will fake a
real OpenOffice.org binary:

    >>> import sys
    >>> write('fake_soffice', 
    ... '''#!%s
    ... import sys
    ... import pprint
    ... sys.stdout.write("Fake soffice started with these options/args:\\n")
    ... pprint.pprint(sys.argv)
    ... sys.stderr.flush()
    ... sys.stdout.flush()
    ... while 1:
    ...     pass
    ... ''' % sys.executable)

This script will simply loop forever (well, sort of). We determine the
exact absolute path of our 'binary':

    >>> import os
    >>> soffice_path = os.path.join(os.getcwd(), 'fake_soffice')

We must make this script executable:

    >>> import os
    >>> os.chmod('fake_soffice', 0700)

Now we can call the daemon and tell it to start our faked office
server:

    >>> print system("%s -b %s start" % (join('bin', 'oooctl'), soffice_path))
    starting OpenOffice.org server, going into background...
    started with pid ...
    <BLANKLINE>

We can get the daemon status:

    >>> print system(join('bin', 'oooctl') + ' status')
    Status: Running (PID ...) 
    <BLANKLINE>


We can stop the server:

    >>> print system(join('bin', 'oooctl') + ' stop')
    stopping pid ... done.
    <BLANKLINE>


(Re-)Directing the daemon input and output
------------------------------------------

By default the daemonized programme's output will be redirected to
``/dev/null``. You can, however use the ``--stdout``, ``--stderr`` and
``--stdin`` options to set appropriate log files.

We create a temporary log file:

    >>> import tempfile
    >>> (tmp_fd, tmp_path) = tempfile.mkstemp()

Now we start the OOo server with the tempfile as logger:

    >>> print system(join('bin', 'oooctl') + ' -b %s start' % (
    ...                                                       soffice_path, )
    ...                                    + ' --stdout="%s"' % tmp_path)
    starting OpenOffice.org server, going into background...
    started with pid ...
    <BLANKLINE>

    >>> print system(join('bin', 'oooctl') + ' stop')
    stopping pid ... done.
    <BLANKLINE>

In the logfile we can see what arguments and options the daemon used:

    >>> cat (tmp_path)
    Fake soffice started with these options/args:
    ['/sample-buildout/fake_soffice',
     '-accept=socket,host=localhost,port=2002;urp;',
     '-headless',
     '-nologo',
     '-nofirststartwizard',
     '-norestore']

``pyunoctl`` -- a conversion daemon
===================================

This script starts a server in background that allows conversion of
documents using the pyUNO API. It requires a running OO.org server in
background (see above).

.. note:: This script must be installed with a pyuno enabled Python interpreter!

  See sections below on how to do/check this.


Currently conversion from all OOo readable formats (.doc, .odt, .txt,
...) to HTML and PDF-A is supported. This means, if you can load a
document with OpenOffice.org, then this daemon can convert it to HTML
or PDF-A.

The conversion daemon starts a server in background which listens for
conversion requests on a TCP port. It then calls OpenOffice.org via
the pyUNO-API to perform the conversion and responses with the path of
the generated doc (or an error message).

The conversion server is a multithreaded asynchronous TCP daemon. So,
several requests can be served at the same time.

The script provides help with the ``-h`` switch:

    >>> print system(join('bin', 'pyunoctl') + ' -h')
    Usage: pyunoctl [options] start|stop|restart|status
    ...

    >>> import os
    >>> old_cwd = os.getcwd() 
    >>> #os.chdir('/')

Before we can really use the daemon, we have to fire up the OOo
daemon:

    >>> print system(join('bin', 'oooctl') + ' --stdout=/tmp/output start')
    starting OpenOffice.org server, going into background...
    started with pid ...
    <BLANKLINE>

Now, we start the pyuno daemon:

    >>> print system(join('bin', 'pyunoctl') + ' --stdout=/tmp/out start')
    starting pyUNO conversion server, going into background...
    started with pid ...
    <BLANKLINE>


Testing the conversion daemon
-----------------------------

Once, the daemon started we can send requests. One of the commands we
can send is to test environment, connection and all that. For this, we
need a client that sends commands and parses the responses for us. It
is not difficult to write an own client (few lines of socket code will
do), but if you're writing third party software you might use the
ready-for-use client from `ulif.openoffice.client`, which should give
you a more consistent API over time and can hide changes in protocol
etc.

Using the client in simple form can be done like this:

    >>> from ulif.openoffice.client import PyUNOServerClient
    >>> def send_request(ip, port, message):
    ...   client = PyUNOServerClient(ip, port)
    ...   result = client.sendRequest(message)
    ...   ok = result.ok and 'OK' or 'ERR'
    ...   return '%s %s %s' % (ok, result.status, result.message)

The client returns response objects, which always contain:

* ``ok``
    a boolean flag indicating whether the request succeeded

* ``status``
    a number indicating the response status. Stati are generally
    leaned on HTTP status messages, so 200 means 'okay' while any
    other number indicates some problem in processing the request.

* ``message``
    Any readable output returned by the server. This includes paths or
    more verbose error messages in case of errors.

Commands sent always have to be closed by newlines:

    >>> command = 'TEST\n'

As the default port is 2009, we can call the client like this:

    >>> print send_request('127.0.0.1', 2009, command)
    OK 0 0.1dev

The response tells us that

* the request could be handled ('OK'),

* the status is zero (=no problems),

* the version number of the server ('0.1dev').

If we send garbage, we get an error:

    >>> command = 'Blah\n'
    >>> print send_request('127.0.0.1', 2009, command)
    ERR 550 unknown command. Use CONVERT_HTML, CONVERT_PDF or TEST.

Here the server tells us, that

* the request could not be handled ('ERR')

* the status is 550

* a hint, what commands we can use to talk to it.

As we can see, we are normally using HTTP status codes. This is also a
measure to allow simple switch to HTTP somewhen in the future.

Before we go on, we have to give the server time to start up:

    >>> import time
    >>> time.sleep(3)


Convert to PDF via the conversion daemon
----------------------------------------

Finally let's start a real conversion. We have a simple .doc document
we'd like to have as PDF. The document is located here:

    >>> import os
    >>> import shutil
    >>> import ulif.openoffice
    >>> src_path = os.path.dirname(ulif.openoffice.__file__)
    >>> src_path = os.path.join( src_path,
    ...                  'tests', 'input', 'simpledoc1.doc')
    >>> dst_path = os.path.join('home', 'simpledoc1.doc')
    >>> shutil.copyfile(src_path, dst_path)
    >>> testdoc_path = os.path.abspath(dst_path)


We tell the machinery to convert to PDF/A by sending the following
lines::

    CONVERT_PDF
    PATH=<path-to-source-document>

We start the conversion:

    >>> command = ('CONVERT_PDF\nPATH=%s\n' % testdoc_path)
    >>> print send_request('127.0.0.1', 2009, command)
    OK 200 /sample-buildout/home/simpledoc1.pdf

The created file is generated at the same path as the source.

We can also use the client component to get convert to PDFs:

    >>> from ulif.openoffice.client import PyUNOServerClient
    >>> client = PyUNOServerClient()
    >>> response = client.convertFileToPDF(testdoc_path)

The response will contain a status (HTTP equivalent number), a boolean
flag indicating whether conversion was performed successfully and a
message, which in case of success contains the path of the generated
document:

    >>> response.status
    200

    >>> response.ok
    True

    >>> response.message
    '/sample-buildout/home/simpledoc1.pdf'

Instead of giving a path, we can also use the client with a
``filename`` parameter and the contents of the file to be
converted. For this, we use the clients ``convertToPDF`` method. This
consumes slightly more time than the method above:

    >>> contents = open(testdoc_path, 'rb').read()
    >>> response = client.convertToPDF(
    ...              os.path.basename(testdoc_path), contents)

Again, the ``message`` attribute of the response tells us, where the
generated doc can be found:

    >>> response.message
    '/.../simpledoc1.pdf'

This time the document was created inside a temporary directory,
created only for this request. You should not make assumptions about
this location.

.. note:: It is the callers responsibility to remove the temporary
          directory after use.

    >>> import shutil
    >>> shutil.rmtree(os.path.dirname(response.message))



Convert to HTML via the conversion daemon
-----------------------------------------

Finally let's start a real conversion. We have a really simple .doc
document we'd like to have as HTML.

We tell the machinery to convert to PDF/A by sending the following
lines::

    CONVERT_HTML
    PATH=<path-to-source-document>

We start the conversion:

    >>> command = ('CONVERT_HTML\nPATH=%s\n' % testdoc_path)
    >>> print send_request('127.0.0.1', 2009, command)
    OK 200 /sample-buildout/home/simpledoc1.html


We can also use the client component to get convert to HTML:

    >>> from ulif.openoffice.client import PyUNOServerClient
    >>> client = PyUNOServerClient()
    >>> filecontent = open(testdoc_path, 'rb').read()
    >>> response = client.convertFileToHTML(testdoc_path)

The response will contain a status (HTTP equivalent number), a boolean
flag indicating whether conversion was performed successfully and a
message, which in case of success contains the path of the generated
HTML document. All embedded files that belong to that document are
stored in the same directory as the HTML file:

    >>> response.status
    200

    >>> response.ok
    True

    >>> response.message
    '/sample-buildout/home/simpledoc1.html'


Instead of giving a path, we can also use the client with a
``filename`` parameter and the contents of the file to be
converted. For this, we use the clients ``convertToHTML`` method. This
consumes slightly more time than the method above:

    >>> contents = open(testdoc_path, 'rb').read()
    >>> response = client.convertToHTML(
    ...              os.path.basename(testdoc_path), contents)

Again, the ``message`` attribute of the response tells us, where the
generated doc can be found:

    >>> response.message
    '/.../simpledoc1.html'

This time the document was created inside a temporary directory,
created only for this request. You should not make assumptions about
this location. All accompanied documents like images, etc. are stored
in the same directory.

.. note:: It is the callers responsibility to clean up generated
     directories.

We must remove the result directory ourselve:

    >>> import shutil
    >>> result_dir = os.path.dirname(response.message)
    >>> if os.path.isdir(result_dir):
    ...   shutil.rmtree(result_dir)


Note, that the user that run OO.org server, will need a valid home
directory where OOo stores data. We create such a home in the
testsetup in the ``home`` directory:

    >>> ls('home')
    d  .fontconfig
    d  .openoffice.org2
    -  simpledoc1.doc
    -  simpledoc1.html
    -  simpledoc1.pdf

Clean up:


Shut down the pyuno daemon:
    >>> print system(join('bin', 'pyunoctl') + ' stop')
    stopping pid ... done.
    <BLANKLINE>

Shut down the oooctl daemon:

    >>> print system(join('bin', 'oooctl') + ' stop')
    stopping pid ... done.
    <BLANKLINE>

    >>> os.close(tmp_fd)
    >>> os.unlink(tmp_path)

