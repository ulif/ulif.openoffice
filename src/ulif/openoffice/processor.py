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
import os
import shutil
import tempfile
from urlparse import urlparse
from ulif.openoffice.cachemanager import (
    CacheManager, CACHE_SINGLE, CACHE_PER_USER)
from ulif.openoffice.convert import convert
from ulif.openoffice.helpers import (
    copy_to_secure_location, get_entry_points, zip, unzip, remove_file_dir,
    extract_css, cleanup_html, cleanup_css, rename_sdfield_tags,
    string_to_bool)

class BaseProcessor(object):
    """A base for self-built document processors.
    """
    #: The name under which this processor is known. A simple string.
    prefix = 'base'

    #: The option defaults. A dictionary. Each option supported by
    #: this processor needs a default value set in this dictionary.
    defaults = {}
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

        The default implementation raises :exc:`NotImplemented`.
        """
        raise NotImplemented("Please provide a process() method")

    def validate_options(self):
        """Examine `self.options` and raise `ValueError` if appropriate.

        The default implementation raises :exc:`NotImplemented`.
        """
        raise NotImplemented("Please provide a validate_options method")

    def get_own_options(self, options):
        """Get options for this class out of a dict of general options.

        Returns a dictionary normally set as `self.options`.
        """
        options = dict([(key, val) for key, val in options.items()
                        if key.startswith(self.prefix + '.')])
        result = dict()
        result.update(self.defaults) # Make sure result is not the
                                     # same as defaults
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

    The :class:`MetaProcessor` is a kind of processor dispatcher that
    finds, setups and calls all requested processors in the wanted
    order.
    """
    #: the meta processor is named 'meta'
    prefix = 'meta'

    #: We support a ``procord`` option which stands for
    #: ``processororder``. The currently default order is:
    #: ``'unzip,oocp,zip'`` which means: maybe unzip the input, then
    #: convert it into HTML and afterwards zip the results.
    defaults = {            # Option defaults. Each option needs one.
        'procord': 'unzip,oocp,tidy,html_cleaner,css_cleaner,zip',
        }

    @property
    def avail_procs(self):
        return get_entry_points('ulif.openoffice.processors')

    def __init__(self, options={}, allow_cache=None, cache_dir=None,
                 cache_layout=CACHE_SINGLE, user=None):
        self.all_options = options
        self.options = self.get_own_options(options)
        self.normalize_options()
        self.validate_options()
        self.metadata = {}
        self.allow_cache = allow_cache
        self.cachedir = cache_dir
        self.cachelayout = cache_layout
        self.user = user
        return

    def validate_options(self):
        """Make sure all options contain valid values.
        """
        for item in self.options['procord'].split(','):
            item = item.strip()
            if item != '' and item not in self.avail_procs.keys():
                raise ValueError('Invalid procord value (%s not in %s)' % (
                        item, self.avail_procs.keys()))
        return

    def process(self, input=None, metadata={'error':False}):
        """Run all processors defined in options.

        If all processors run successful, the output of the last along
        with (maybe modified) metadata is returned.

        Each processor is fed with the `metadata` dict and an `input`
        (normally a filepath). Feeding a processor means to call its
        `process` method.

        If a processor sets the ``error`` entry of `metadata` to
        ``True`` this indicates some problem and the whole process is
        aborted returning ``None`` as output and the `metadata`, maybe
        containing some smart hints about the reasons.

        If all processors work correctly, the output of the last
        processor is returned along with the last `metadata`.

        The set and order of processors called depends on the
        ``procord`` option passed in. If this option is set to some
        value like ``oocp,oocp`` then the ``oocp`` processor (which is
        the :class:`OOConvProcessor`, registered under ``oocp`` in
        `setup.py`) is called two times.

        .. note:: after each processing, the (then old) input is
                  removed.
        """
        metadata = metadata.copy()
        pipeline = self._build_pipeline()
        output = None
        for processor in pipeline:
            proc_instance = processor(self.all_options)
            #try:
            output, metadata = proc_instance.process(input, metadata)
            #except:
            # metadata['error'] = True
            if metadata['error'] is True:
                metadata = self._handle_error(
                    processor, input, output, metadata)
                return None, metadata
            if input != output:
                remove_file_dir(input)
            input = output
        return input, metadata

    def _handle_error(self, proc, input, output, metadata):
        metadata['error-descr'] = metadata.get(
            'error-descr',
            'problem while processing %s' % proc.prefix)
        remove_file_dir(input)
        remove_file_dir(output)
        return metadata

    def _build_pipeline(self):
        """Build a pipeline of processors according to options.
        """
        result = []
        for option, avail_dict in [('procord', self.avail_procs),]:
            for key in self.options[option].split(','):
                if key == '' or key == 'meta':
                    # Ignore non-processors...
                    continue
                result.append(avail_dict[key])
        result = tuple(result)
        return result

class OOConvProcessor(BaseProcessor):
    """A processor that converts office docs into different formats.

    XXX: we could support far more options. See

         http://wiki.services.openoffice.org/wiki/API/Tutorials/PDF_export#How_to_use_it_from_OOo_Basic

         only for a list of PDF export options.
    """
    prefix = 'oocp'

    defaults = {
        'out_fmt': 'html',
        'pdf_version': None,
        'pdf_tagged': None,
        'host' : 'localhost',
        'port': 2002,
        }

    formats = {
        "txt": "Text (Encoded)",
        "pdf": "writer_pdf_Export",
        "html": "HTML (StarWriter)",
        "xhtml": "XHTML Writer File",
        }

    options = {}

    def _get_filter_props(self):
        props = []
        if self.options['pdf_version'] is not None:
            # allowed: 0L (PDF1.4), 1L (PDF1.3 aka PDF1/A)
            value = long(self.options['pdf_version'])
            props.append(
                ("SelectPdfVersion", 0, value, 0))
        if self.options['pdf_tagged'] is not None:
            # allowed: True, False
            value = string_to_bool(self.options['pdf_tagged']) or False
            props.append(
                ("UseTaggedPDF", 0, value, 0))
        return props

    def process(self, path, metadata):
        basename = os.path.basename(path)
        src = os.path.join(
            copy_to_secure_location(path), basename)
        if os.path.isfile(path):
            path = os.path.dirname(path)
        shutil.rmtree(path)
        extension = self.options['out_fmt']
        filter_name = self.formats[extension]
        url = 'uno:socket,host=%s,port=%d;urp;StarOffice.ComponentContext' % (
            self.options['host'], self.options['port'])

        filter_props = self._get_filter_props()
        status, result_paths = convert(
            url=url,
            extension=extension, filter_name=filter_name,
            filter_props=filter_props, paths=[src]
            )

        metadata['oocp_status'] = status
        if status != 0:
            metadata['error'] = True
            metadata['error-descr'] = 'conversion problem'
            shutil.rmtree(src)
            return None, metadata
        result_path = urlparse(result_paths[0])[2]

        # Remove input file if different from output
        if os.path.exists(src):
            if os.path.basename(result_path) != basename:
                os.unlink(src)
        return result_path, metadata

    def validate_options(self):
        if not self.options['out_fmt'] in self.formats.keys():
            raise ValueError(
                "Invalid out_fmt: %s not in [%s]" % (
                    self.options['out_fmt'], ", ".join(self.formats.keys()))
                )
        return

class UnzipProcessor(BaseProcessor):
    """A processor that unzips delivered files if applicable.

    The .zip file might contain only exactly one file.
    """
    prefix = 'unzip'

    supported_extensions = ['.zip',]
    def validate_options(self):
        # No options to handle...
        pass

    def process(self, path, metadata):
        ext = os.path.splitext(path)[1]
        if not ext in self.supported_extensions:
            return path, metadata
        if ext == '.zip':
            dst = tempfile.mkdtemp()
            unzip(path, dst)
            dirlist = os.listdir(dst)
            if len(dirlist) != 1 or os.path.isdir(
                os.path.join(dst, dirlist[0])):
                metadata['error'] = True
                metadata['error-descr'] = 'ambiguity problem: several files'
                shutil.rmtree(dst)
                return None, metadata
            path = os.path.join(dst, dirlist[0])
        return path, metadata

class ZipProcessor(BaseProcessor):
    """A processor that zips the directory delivered.
    """
    prefix = 'zip'

    supported_extensions = ['.zip']
    def validate_options(self):
        # No options to handle...
        pass

    def process(self, path, metadata):
        if isinstance(path, unicode):
            # zipfile does not accept unicode encoded paths...
            path = path.encode('utf-8')
        if os.path.isfile(path):
            basename = os.path.basename(path)
        path = os.path.dirname(path)
        zip_file = zip(path)
        shutil.rmtree(path)
        result_path = os.path.join(
            os.path.dirname(zip_file), basename + '.zip')
        os.rename(zip_file, result_path)
        return result_path, metadata

class Tidy(BaseProcessor):
    """A processor for cleaning up HTML code produced by OO.org output.

    This processor calls :cmd:`tidy` in a subshell. That means the
    :cmd:`tidy` command must be installed in system to make this
    processor work.
    """
    prefix = 'tidy'

    def validate_options(self):
        # No options to handle yet...
        pass

    def process(self, path, metadata):
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        src_dir = os.path.dirname(src_path)
        remove_file_dir(path)

        # Remove <SDFIELD> tags if any
        cleaned_html = rename_sdfield_tags(open(src_path, 'rb').read())
        open(src_path, 'wb').write(cleaned_html)

        error_file = os.path.join(src_dir, 'tidy-errors')
        cmd = 'tidy -asxhtml -clean -indent -modify -utf8 -f %s %s' % (
            error_file, src_path)
        os.system(cmd)
        os.unlink(error_file)
        return src_path, metadata

class CSSCleaner(BaseProcessor):
    """A processor for cleaning up CSS parts of HTML code.

    Normal converters leave CSS inside an HTML document. This
    processor first aggregates these style parts and then puts it into
    an external CSS file leaving only a link to that file.

    This processor requires HTML/XHTML input.
    """
    prefix = 'css_cleaner'

    defaults = {
        'minified': True,
        }

    def validate_options(self):
        minified = self.options.get('minified')
        if minified is not True:
            self.options['minified'] = string_to_bool(minified)
            if self.options['minified'] is None:
                raise ValueError("`minified' must be true or false.")
        return

    def process(self, path, metadata):
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        src_dir = os.path.dirname(src_path)
        remove_file_dir(path)

        new_html, css = extract_css(open(src_path, 'rb').read(), basename)
        css, errors = cleanup_css(css, minified=self.options['minified'])

        css_file = os.path.splitext(src_path)[0] + '.css'
        if css is not None:
            open(css_file, 'wb').write(css)
        open(src_path,'wb').write(new_html)

        return src_path, metadata

class HTMLCleaner(BaseProcessor):
    """A processor for cleaning up HTML produced by OO.org.

    Fixes minor issues with HTML code produced by OO.org.

    This processor expects XHTML input input.
    """
    prefix = 'html_cleaner'

    defaults = {
        'fix_head_nums': True,
        'fix_img_links': True,
        'fix_sdfields': True,
        }

    def validate_options(self):
        for option_name in ['fix_head_nums', 'fix_img_links', 'fix_sdfields']:
            opt_value = self.options.get(option_name)
            if opt_value is not True:
                self.options[option_name] = string_to_bool(opt_value)
                if self.options[option_name] is None:
                    raise ValueError(
                        "`%s' must be true or false." % option_name)
        return

    def process(self, path, metadata):
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        src_dir = os.path.dirname(src_path)
        remove_file_dir(path)

        new_html, img_name_map = cleanup_html(
            open(src_path, 'rb').read(), basename,
            fix_head_nums=self.options['fix_head_nums'],
            fix_img_links=self.options['fix_img_links'],
            fix_sdfields=self.options['fix_sdfields'],
            )
        open(src_path,'wb').write(new_html)
        # Rename images
        self.rename_img_files(src_dir, img_name_map)
        return src_path, metadata

    def rename_img_files(self, src_dir, img_name_map):
        for old_img, new_img in img_name_map.items():
            old_path = os.path.join(src_dir, old_img)
            new_path = os.path.join(src_dir, new_img)
            if not os.path.isfile(old_path):
                # XXX: Update error messages
                continue
            if os.path.exists(new_path):
                # XXX: Update error messages
                continue
            shutil.move(old_path, new_path)
        return

class Error(BaseProcessor):
    """A processor that returns an error message.

    This is mainly for testing.
    """
    prefix = 'error'

    def validate_options(self):
        # No options to handle yet...
        pass

    def process(self, path, metadata):
        metadata.update(
            {'error-descr': 'Intentional error. Please ignore',
             'error': True})
        return None, metadata
