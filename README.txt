ulif.openoffice
***************

Bridging Python and OpenOffice.org.

This package provides tools like daemons and converters to ease access
to OpenOffice.org installations for Python programmers.

What does `ulif.openoffice` provide?

* ``oooctl``

  A commandline script to start/stop OpenOffice.org as a daemon
  (without X)

.. note:: POSIX-only!

  The tools provided by `ulif.openoffice` run on POSIX systems (like
  Linux) only!


Prerequisites
=============

There are, unfortunately, zillions of possibilities why you cannot
start OpenOffice.org as in background on a system.

The scripts in here were tested with Ubuntu and work.

If you want to use a Ubuntu (or Debian) prepared install of OOo, you
must make sure, that you apt-get-installed the following packages:

* ``openoffice.org-headless``

* ``openoffice.org-java-common``

additionally to the usual OOo packages.
