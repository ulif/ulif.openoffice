ulif.openoffice
***************

Connect LibreOffice/OpenOffice, Python, and The Web.

This package provides tools like WSGI apps, cache managers, and
commandline converters to ease access to LibreOffice/OpenOffice
installations for Python programmers. Beside basic converting it
provides 'document processors' for further finetuning of generated
docs (mainly HTML).

Out of the box these processors allow extracting CSS from HTML
conversions, removal of LibreOffice-specific tags, zipping, unzipping,
etc.

If the given processors are not enough for you, or you want some
special handling of results (say, sign the generated doc
cryptographically, add watermarks or whatever), you can define own
additional document processors in your own packages by using the
Python entry-point API. `ulif.openoffice` will integrate them
automatically during document processing and provide them in
webservices, commandline clients and Python API.

.. note:: `ulif.openoffice` trusts `unoconv` to do the actual
          conversions. So you must have the `unoconv` script installed
          on your system.

Resources
=========

`ulif.openoffice` sources are hosted on

  https://github.com/ulif/ulif.openoffice

The complete documentation can be found at

  https://ulif-openoffice.readthedocs.org/en/latest/


.. contents::

..
    >>> from ulif.openoffice.testing import (
    ...     doctest_setup, doctest_teardown, doctest_rm_resultdir)
    >>> doctest_setup()

Examples
========

Conversion via Python
---------------------

A .doc to .html conversion via the Python API can be done like this::

    >>> from ulif.openoffice.client import Client
    >>> client = Client()
    >>> result = client.convert('document.doc')
    >>> result
    ('.../document.html.zip', None, {'oocp_status': 0, 'error': False})

..
    >>> doctest_rm_resultdir(result[0])         # clean up

The generated document is by default brushed up HTML with separate
stylesheets and images all put into a single .zip document.

You can configure the document conversion via various options. This
way you can set the output type (at least PDF, HTML, XHTML and TXT are
supported), tell whether separate CSS stylesheets should be extracted,
which PDF format should be generated (1.3 aka PDF/A or 1.4), and many,
many things more.

Conversion via Commandline
--------------------------

We also provide a handy commandline tool to perform conversions::

    $ oooclient document.doc
    RESULT in /tmp/.../document.html.zip

As you can see, the result is put in a freshly created directory.

The commandline client also provides help to display all supported
options, document processors, etc.::

    $ oooclient --help

will give you the comprehensive list.


Conversion via Web
------------------

`ulif.openoffice` comes with a WSGI application that provides a
RESTful document conversion service. With this application running you
can send office documents to a webserver and will receive the
converted document.

The WSGI document converter supports (optional) local caching which
will store conversion results and deliver it (bypassing new
conversion) if a document was requested to be converted already.


Install
=======

User Install
------------

`ulif.openoffice` can be installed via `pip`::

    $ pip install ulif.openoffice

Afterwards all commandline tools should be available.


Developer Install
-----------------

It is recommended to setup sources in a virtual environment::

    $ virtualenv py27      # Python 2.6, 2.7 are supported
    $ source py27/bin/activate
    (py27) $

Get the sources::

    (py27) $ git clone https://github.com/ulif/ulif.openoffice.git
    (py27) $ cd ulif.openoffice

Install packages for testing::

    (py27) $ python setup.py dev

It is recommended to start the ``oooctl`` daemon before running
tests::

    (py27) $ oooctl start

This will make LibreOffice listen in background and reduce
runtime of tests significantly.

Running tests::

    (py27) $ py.test

We also support `tox` to run tests for all supported Python versions::

    (py27) $ pip install tox
    (py27) $ tox

Of course you must have the respective Python versions installed
(currently: Python 2.6, 2.7).

Running coverage detector::

    (py27) $ py.test --cov=ulif.openoffice    # for cmdline results
    (py27) $ py.test --cov=ulif.openoffice --cov-report=html

The latter will generate HTML coverage reports in a subdirectory.

Install packages for Sphinx-base documentation::

    (py27) $ python setup.py docs
    (py27) $ cd doc
    (py27) $ make html

Will generate the documentation in a subdirectory.


License
=======

`ulif.openoffice` is covered by the GPL version 2.


Author
======

By Uli Fouquet (uli at gnufix dot de). Please do not hesitate to
contact me for wishes, requests, suggestions, or other questions.

..
    >>> doctest_teardown()
