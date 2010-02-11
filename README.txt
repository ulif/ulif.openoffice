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

It is mandatory, that the system user running ``oooctl`` is a regular
user with at least a home directory. OpenOffice.org relies on that
directory to store information even in headless mode.

Recent OpenOffice.org versions require no X-server for running.

If you want to use a Ubuntu (or Debian) prepared install of OOo, you
must make sure, that you apt-get-installed the following packages:

* ``openoffice.org-headless`` (for Ubuntu < 9.04, not needed for newer)

* ``openoffice.org-java-common``

additionally to the usual OOo packages, i.e.:

* ``openoffice.org`` (at least for Ubuntu >= 9.04)

Then, you need at least one Python version, which supports::

  $ python -c "import uno"

without raising any exceptions.

On newer Ubuntu versions you can install::

* ``python-uno`` (if available)

The clients and other software apart from the oooctl-server and the
pyuno-server can be run with a different Python version.

If you successfully installed this package on a different system, we'd
be glad to hear from you, especially, if you could tell, what
system-packages you used.


Building
========

First make sure, that you entered your UNO-supporting Python version
in buildout.cfg. By default it will assume, that this is
/usr/bin/python.

If::

  $ /usr/bin/python -c "import uno"

gives an exception on your system, you must edit buildout.cfg, section
``[unopython]``, to tell where the supporting Python can be found.

Then run

  $ python bootstrap/bootstrap.py

with the Python version, your client should later run with. This can
be the UNO-supporting Python but don't has to.

This way you can, for example, use the client components with Python
2.4 while the ooo-server and pyuno-server will run with Python 2.6.

After running bootstrap.py, do::

  $ ./bin/buildout

which will create all scripts in bin/.

Using the scripts
=================

There are four main components that come with ``ulif.openoffice``:

* an oooctl-server that starts OpenOffice.org in background.

* a pyuno-server that listens for requests to convert docs. This
  server depends on a running oooctl-server.

* a client component that can be accessed via API and can talk to the
  pyuno-server. This way you can convert docs from Python and the
  Python version has not to provide the uno lib.

* a converter script (also in ./bin), you can use on the
  commandline. It depends on a running oooctl server and can convert
  docs to .txt, .html and .pdf format. It is merely a little test
  programme that was used during development, but you might have some
  use for it.

You can start the oooctl-server with::

  $ ./bin/oooctl start

Do::

  $ ./bin/oooctl --help

to see all options.

You can stop the daemon with::

  $ ./bin/oooctl stop

The same applies to the pyuno-server::

  $ ./bin/pyunoctl start
  $ ./bin/pyunoctl --help
  $ ./bin/pyunoctl stop

do what you think they do.

The converter script can be called like this::

  $ ./bin/convert sourcefile.doc

to create a sourcefile.txt conversion.

Do::

  $ ./bin/convert --pdf sourcefile.doc

to create a PDF of sourefile.doc, and

  $ ./bin/convert --html sourcefile.doc

to create an HTML version of sourcefile.doc.

For the client API see the .txt files in the source.
