##
## processor.py
## Login : <uli@pu.smp.net>
## Started on  Sat Apr 30 02:56:12 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
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
Processors for processing documents.
"""
from pkg_resources import iter_entry_points

class BaseProcessor(object):
    prefix = 'base'         # The name under which this proc is known
    defaults = {}           # Option defaults. Each option needs one.
    metadata = {}

    def __init__(self, options={}):
        self.options = self.get_own_options(options)
        self.normalize_options()
        self.validate_options()
        self.metadata = {}
        return

    def process(self, input, metadata):
        """Process the input and return output.

        `metadata` contains data maybe valuable for other
        processors. Derived classes are encouraged to populate this
        dictionary while it cannot be guaranteed that other processors
        make use of this data.

        `output` is expected to be a tuple

          ``(<OUTPUT>, <METADATA>)``

        where ``<OUTPUT>`` would normally be the path to a file and
        ``<METADATA>`` the (maybe updated) `metadata` passed in.
        """
        raise NotImplemented("Please provide a process() method")

    def validate_options(self):
        """Examine `self.options` and raise `ValueError` if appropriate.
        """
        raise NotImplemented("Please provide a validate_options method")

    def get_own_options(self, options):
        """Get options for this class out of a dict of general options.
        """
        options = dict([(key, val) for key, val in options.items()
                    if key.startswith(self.prefix + '.')])
        result = self.defaults
        for key, val in options.items():
            key = key[len(self.prefix)+1:]
            if key not in dict(self.defaults).keys():
                # Ignore...
                continue
            result[key] = val
        return result

    def get_options_as_string(self):
        """Get a string representation of the options used here.

        This is important to get valid hashes for different sets of
        options. From this representation hashes might be used by the
        cache manager to find already processed docs.

        To make caching effective, each set of option-settings that
        leads to the same result should have the same string
        representation.
        """
        result = ""
        for key in sorted(self.options):
            result += "%s=%s" % (key, self.options[key])
        return result

    def normalize_options(self):
        for key, val in self.options.items():
            if not isinstance(val, basestring):
                continue
            val = ','.join([x.strip() for x in val.split(',')])
            self.options[key] = val
        return


class MetaProcessor(BaseProcessor):
    """The meta processor handles general workflow.

    When getting certain options, it constructs a pipeline of document
    processors.
    """
    prefix = 'meta'         # The name under which this proc is known
    defaults = {            # Option defaults. Each option needs one.
        'prepord': '',
        'procord': 'oocp',
        'postpord': '',
        }

    @property
    def avail_preps(self):
        return dict(
            [(x.name, x.load()) for x in
             iter_entry_points(group='ulif.openoffice.preprocessors')])

    @property
    def avail_procs(self):
        return dict(
            [(x.name, x.load()) for x in
             iter_entry_points(group='ulif.openoffice.processors')])

    @property
    def avail_postps(self):
        return dict(
            [(x.name, x.load()) for x in
             iter_entry_points(group='ulif.openoffice.postprocessors')])

    def validate_options(self):
        """Make sure all options contain valid values.
        """
        for option, avail_dict in [
            ('prepord', self.avail_preps),
            ('procord', self.avail_procs),
            ('postpord', self.avail_postps)]:
            for item in self.options[option].split(','):
                item = item.strip()
                if item != '' and item not in avail_dict.keys():
                    raise ValueError('Invalid %s value (%s not in %s)' % (
                            option, item, avail_dict.keys()))
        return

    def process(self, input=None, metadata={}):
        """Run all processors defined in options.
        """
        self._build_pipeline()
        output = None
        for processor in self._pipeline:
            output, metadata = processor.process(input, metadata)
            input = output
        return output, metadata

    def _build_pipeline(self):
        """Build a pipeline of processors according to options.
        """
        result = []
        for option, avail_dict in [
            ('prepord', self.avail_preps),
            ('procord', self.avail_procs),
            ('postpord', self.avail_postps)]:
            for key in self.options[option].split(','):
                if key == '':
                    continue
                result.append(avail_dict[key])
        result = tuple(result)
        self._pipeline = result
        return

class OOConvProcessor(BaseProcessor):
    """A processor that converts office docs into different formats.
    """
    prefix = 'oocp'

    defaults = {
        'out_fmt': 'html',
        'pdf_version': None,
        'pdf_tagged': None,
        }

    formats = {
        "txt": "Text (Encoded)",
        "pdf": "writer_pdf_Export",
        "html": "HTML (StarWriter)",
        "xhtml": "XHTML Writer File",
        }

    def process(self, path, options):
        myoptions = [(key, val) for key, val in options
                     if key.startswith(self.prefix + '.')]
        pass

    def validate_options(self):
        if not self.options['out_fmt'] in self.formats.keys():
            raise ValueError(
                "Invalid out_fmt: not in [%s]" % ", ".join(self.formats.keys())
                )
        return
