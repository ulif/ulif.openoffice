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
from argparse import ArgumentParser
from ulif.openoffice.helpers import get_entry_points

#: Regular expression to check short argument names like ``-opt``.
RE_SHORT_NAME = re.compile('^-[a-zA-Z0-9][a-zA-Z0-9\-_]*$')

#: Regular expression to check long argument names like ``--option``.
RE_LONG_NAME = re.compile('^--[a-zA-Z0-9][a-zA-Z0-9\-_]+$')


def dict_to_argtuple(arg_dict):
    result = []
    for key in sorted(arg_dict.keys()):
        result.extend(('-' + key, arg_dict[key]))
    return tuple(result)


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


class ArgumentParserError(Exception):
    pass


class ExceptionalArgumentParser(ArgumentParser):

    def error(self, message):
        raise ArgumentParserError(message)


class Options(dict):
    """Options are dicts that automatically set processor options.

    Different to regular dicts, `Options` can be constructed with a
    dict of values or a dict of string-values (or both; in this case
    real values have precedence over string-values).

    `string_dict` values (if passed in) are set via an argparse
    ArgumentParser. To override any processor option's default value,
    the key must be eqal to the respective processor option's short
    name (without leading dash). For example you could override the
    `--oocp-output-format` option by passing in
    ``string_dict={'oocp-out-fmt': 'pdf'}``. Please note that here the
    key contains dashes instead of underscores.

    The values of `string_dict` dicts are expected to be strings, for
    example as sent by web forms. As `string_dicts` are fed to an
    argparse.ArgumentParser instance, they allow only keys available
    as short name of any existing and registered processor.

    `val_dict` values (if passed in) are set as such. I.e. `'True'`
    will be set as the string `'True'` and not as the boolean value
    `True`. To override any processor option's default value, the key
    must be equal to the respective processor option long name, with
    dashes turned to underscores and no leading dash. For example you
    could override the `--oocp-output-format` option by passing in
    ``val_dict={'oocp_output_format': 'pdf'}``.
    """

    @property
    def avail_procs(self):
        """A dict of registered processors.

        Keys are the processor names (normally equal to their
        respective prefix). Values are the classes implementing the
        respective processor.
        """
        return get_entry_points('ulif.openoffice.processors')

    @property
    def string_keys(self):
        """Get a list of acceptable keys for string_dicts.

        Acceptable string keys are the short names of options defined
        by processors without the leading dot. For instance the
        `OOCPProcessor` provides an option ``-oocp-host``. The
        respective string key for this option therefore would be:
        ``oocp-host``.

        Currently available options provided by core processors:

            >>> Options().string_keys     # doctest: +NORMALIZE_WHITESPACE
            ['css-cleaner-min',
             'html-cleaner-fix-head-nums',
             'html-cleaner-fix-img-links',
             'html-cleaner-fix-sd-fields',
             'meta-procord',
             'oocp-host',
             'oocp-out-fmt',
             'oocp-pdf-tagged',
             'oocp-pdf-version',
             'oocp-port']

        So, you can create an `Options` dict with overridden defaults
        for instance by passing in something like
        ``string_dict={'oocp-out-fmt': 'pdf'}``.
        """
        result = []
        for proc in self.avail_procs.values():
            result.extend([x.short_name[1:] for x in proc.args])
        return sorted(result)

    def __init__(self, val_dict=None, string_dict=None):
        super(Options, self).__init__()
        args = []
        if string_dict is not None:
            args = dict_to_argtuple(string_dict)
        parser = self.get_arg_parser()
        defaults, trash = parser.parse_known_args(args)
        self.update(vars(defaults))
        if val_dict is not None:
            self.update(val_dict)

    def get_arg_parser(self):
        """Get an :class:`argparse.ArgumentParser` instance.

        The parser will be set up with the options of all registered
        processors.
        """
        parser = ExceptionalArgumentParser()
        # set defaults
        for proc_name, proc in self.avail_procs.items():
            for arg in proc.args:
                parser.add_argument(
                    arg.short_name, arg.long_name, **arg.keywords)
        return parser
