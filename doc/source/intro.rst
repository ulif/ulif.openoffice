Introduction
************

About `ulif.openoffice`
=======================

``ulif.openoffice`` is a Python package to support document
conversions using LibreOffice/OpenOffice.org (LO).

It provides components to interact with a running LO-server for
document conversions from office-type documents like .doc or .odt to
HTML or PDF (to be extended). Using ulif.openoffice you can trigger
such conversions via commandline, programmatically from Python, or via
HTTP.

Furthermore, it provides a caching server that caches all documents
once converted and delivers them in case a document is requested
again. Depending on your needs this can speed-up things by factor 10
or more.

Finally there is also a daemon (``oooctl``) included that starts the
LO server in background and restarts it in case of crashes.


Sources
=======

``ulif.openoffice`` is hosted on:

  http://pypi.python.org/pypi/ulif.openoffice

where you can get latest released versions.

Development can be tracked on github:

  https://github.com/ulif/ulif.openoffice

The documentation can be browsed on:

  https://ulif-openoffice.readthedocs.io/en/latest/


Requirements
============

``ulif.openoffice`` requires `unoconv`_ executable to do the actual
conversions. Current Debian-based distributions normally offer install
of `unoconv`_.

``ulif.openoffice`` is tested on Debian-based systems, most notably
Ubuntu. It will probably miserably fail on Windows and there are no
plans to change that.

The package is designed for server-based deployments. While the
LO-server is running, you cannot use the office-suite on your desktop
(at least at time of writing this). This is a limitation of LO
itself.


Overview
========

``ulif.openoffice`` mainly provides six different components, of which
four merely act as 'frontends' for the core functionality: a cmdline
client, a RESTful WSGI_ application, a WSGI_ based XMLRPC application,
and the respective API calls for use from Python programmes.

* Additional to plain LibreOffice conversions, we provide a set of
  filters to modify office documents on the fly. We call these filters
  ``document processors``. They can unzip incoming docs, zip results,
  extract CSS stylesheets from generated HTML into own files, brush up
  generated HTML and much more. You can always tell which filters to
  apply for each conversion and in what order.

  You can even register your own document processors and they will
  appear in the frontends (cmdline client, WSGI app, API calls).

* An ``oooctl`` server that runs in background, starts a local
  LO-server and monitors its status. If the LO server process dies, it
  is restarted by ``oooctl``.

* An ``oooclient`` commandline tool to trigger conversions.

  ``oooclient`` also supports use of a cache manager that
  caches already converted documents and delivers them in case the
  converted version exists already.

* A DocumentConverter WSGI_ application that acts as a REST_
  server. You can send it documents via HTTP and will get the
  converted documents back.

  The DocumentConverter also supports use of a cache manager that
  caches already converted documents and delivers them in case the
  converted version exists already.

* A WSGIXMLRPC application that also acts as a WSGI_ application but
  provides XMLRPC services. You can use it for instance via the
  standard Python `xmlrpclib` library.

* A Python API to perform all the conversion stuff in your own Python
  programmes.


The components play together roughly as shown in the following figure:

  .. figure:: overview.png

     Fig. 1: Overview of ulif.openoffice components

The black arrows show the way from a source document (in .doc format)
to the LibreOffice server and the way back of the converted document
(PDF).

Use of client-API, ``oooctl`` server and cache is optional.

The LibreOffice server can run on a remote machine.

.. _unoconv: http://dag.wieers.com/home-made/unoconv/
.. _WSGI: http://www.wsgi.org/
.. _REST: http://en.wikipedia.org/wiki/Representational_state_transfer
