Detailed Description
********************

``oooctl``
==========

We can start an OpenOffice.org server using the `oooctl` script.

We define a buildout script that will install the script:

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

