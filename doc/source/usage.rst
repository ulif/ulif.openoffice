Using the scripts
=================

There are two commandline-oriented scripts that come with
``ulif.openoffice``:

* an oooctl-server that starts LibreOffice server in background.

* a converter script called ``oooclient``. It is merely a little test
  programme that was used during development, but you might have some
  use for it. Especially the `--help` option might be interesting, to
  get an overview over the available document processors and their
  options.

Assuming you acticated the virtual environment where the package was
installed (or installed the package otherwise accessible) you can
start the oooctl-server with::

  (py27) $ oooctl start

Do::

  (py27) $ oooctl --help

to see all options.

You can stop the daemon with::

  (py27) $ oooctl stop

The converter script can be called like this::

  (py27) $ oooclient sourcefile.doc

to create a sourcefile.html.zip conversion. The ZIP file will (beside
the generated HTML document) contain all images and extracted CSS
styles.

Do::

  (py27) $ oooclient -meta-procord=oocp, -oocp-out-fmt=pdf sourcefile.doc

to create a PDF of sourefile.doc.
