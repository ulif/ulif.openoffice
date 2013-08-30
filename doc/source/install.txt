Prerequisites
=============

Of course LibreOffice (or OpenOffice) must be installed on the
system. Also unoconv is mandatory.

The scripts in here were tested with Ubuntu and work.

It is mandatory, that the system user running ``oooctl`` is a regular
user with at least a home directory. LibreOffice relies on that
directory to store information even in headless mode.

Recent LibreOffice versions require no X-server for running.

Normally, it should be sufficient to apt-get install unoconv. This
should also install all the office packages needed.

Apart from this, you need Python 2.6 or 2.7 installed. The formerly
required python-uno package is not needed anymore (but unoconv might
require it). Also self-compiled Python variants should work.

Building
========


User Install
------------

You can use pip to install `ulif.openoffice`::

  $ pip install ulif.openoffice

will install the latest released version from PyPI.


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
