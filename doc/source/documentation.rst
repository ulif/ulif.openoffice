*********************
About these documents
*********************

These documents are generated from `reStructuredText
<http://docutils.sf.net/rst.html>`_ sources by *Sphinx*, an excellent
document processor specifically written for the Python documentation
by Georg Brandl and contributors.

Development of this documentation is organized by Uli Fouquet (``uli
at gnufix dot de``). We're always looking for volunteers wanting to
help with the docs, so feel free to send a mail there!

Many thanks go to:

* the `docutils <http://docutils.sf.net/>`_ project for creating
  reStructuredText and the docutils suite;
* Georg Brandl for his `sphinx` package.

See :ref:`reporting-bugs` for information how to report bugs in Python itself.


Building the Documentation
==========================

It's quite easy. Do the developer install as described. Then, in an
activated virtualenv, do::

  (py27)$ python setup.py doc

This fill fetch and install Sphinx.

Now we can build the docs::

  (py27)$ cd doc
  (py27)$ make html

That's it.

Please note, that doctests are done by py.test. The doctests run with
Sphinx will fail.
