##
## options.py
##
## Copyright (C) 2013 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
"""
Components to configure processors.
"""
import re

#: Regular expression to check short argument names like ``-opt``.
RE_SHORT_NAME = re.compile('^-[a-zA-Z0-9][a-zA-Z0-9\-_]*$')

#: Regular expression to check long argument names like ``--option``.
RE_LONG_NAME = re.compile('^--[a-zA-Z0-9][a-zA-Z0-9\-_]+$')


class Argument(object):
    """An argument is a set of args and keywords for argparsers.

    Contains of a `short_name`, an optional `long_name` and any
    keywords. Typical use would be::

      Argument('-myproc', '--my-option', choices=[1, 2, 3])

    When used with :class:`ulif.openoffice.processor.BaseProcessor` or
    derived classes, please make sure that option names start with a
    dash (short options) and a double dash (long options). Furthermore
    each option (whether long or short) should begin with the
    processor prefix: ``-myproc-myopt, --myproc-myoption`` for
    example to avoid clashes with other processors options.
    """
    def __init__(self, short_name, long_name=None, **kw):
        if not RE_SHORT_NAME.match(short_name):
            raise ValueError(
                'Argument short names must have format `-proc-name`')
        if long_name is not None and not RE_LONG_NAME.match(long_name):
            raise ValueError(
                'Argument long names musts have format `--proc-name`')
        self.short_name = short_name
        self.long_name = long_name
        self.keywords = kw
