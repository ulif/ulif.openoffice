ulif.openoffice
***************

LibreOffice/OpenOffice as a RESTful webservice.

This package provides tools like WSGI apps and converters to ease
access to OpenOffice.org/LibreOffice installations for Python
programmers.

The main purpose of the whole package is to provide support for
converting office documents from Python using
OpenOffice.org/LibreOffice but without the need to have PyUNO support
with the Python binary that actually runs your Python application
(like Plone, for instance).

It is based on `unoconv` to do the actual conversions.

The complete documentation of the most recent release can be found at

 http://packages.python.org/ulif.openoffice/

.. contents::

What does `ulif.openoffice` provide?

* ``oooctl``

  A commandline script to start/stop OpenOffice.org as a daemon
  (without X). While OOo brings this functionality out-of-the-box, the
  deamon also monitors status of the OOo server and restarts it if
  necessary.

* ``pyunoctl``

  A commandline script to start/stop a converter daemon, that listens
  for requests to convert office documents from .odt, .doc, .docx,
  etc. to HTML or PDF using OpenOffice.org. Includes a caching
  mechanism that holds docs already converted.

* An API to access any pyunoctl daemon programmatically using Python.

.. note:: POSIX-only!

  The tools provided by `ulif.openoffice` run on POSIX systems (like
  Linux) only!
