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

To do so we creaze a `buildout.cfg` file:

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

Now we can run buildout to install our script:

    >>> print system(join('bin', 'buildout'))
    Installing openoffice-ctl.
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
    ...                                    + ' --stdout="%s"' % tmp_path
    ...                                    + ' --stderr="%s"' % tmp_path)
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

Clean up:

    >>> os.close(tmp_fd)
    >>> os.unlink(tmp_path)
