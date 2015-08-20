#
# processor.py
#
# Copyright (C) 2011, 2013, 2015 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
"""
Processors for processing documents.

The processors defined here do the heavy lifting when converting
documents. All processors accept some input and create some output,
which is normally some file to be converted and handled in different
ways.

While all processors are equal (concerning the basic workflow), one
processor is more equal than others: the :class:`MetaProcessor`. It
collects and coordinates the other processors, creates a pipeline and
other things more. Therefore, to start processing a document, it is
sufficient for callers to get an instance of :class:`MetaProcessor`.

All processors got some `prefix` which is needed to inject any
parameters when processing happens. So, ``oocp.out_fmt`` means setting
or reading the ``out_fmt`` parameter of the ``oocp`` processor or,
more accurate: the processor with `prefix` ``oocp`` (which happens to
be the :class:`OOConvProcessor`, see below).
"""
import os
import shutil
import tempfile
from ulif.openoffice.convert import convert
from ulif.openoffice.helpers import (
    copy_to_secure_location, get_entry_points, zip, unzip, remove_file_dir,
    extract_css, cleanup_html, cleanup_css, rename_sdfield_tags,
    string_to_stringtuple)
from ulif.openoffice.helpers import strict_string_to_bool as boolean
from ulif.openoffice.options import Argument, Options


#: The default order, processors are run.
DEFAULT_PROCORDER = 'unzip,oocp,tidy,html_cleaner,css_cleaner,zip'


def processor_order(string):
    proc_tuple = string_to_stringtuple(string)
    proc_names = get_entry_points('ulif.openoffice.processors').keys()
    for name in proc_tuple:
        if name not in proc_names:
            raise ValueError('Only values in %r are allowed.' % proc_names)
    return proc_tuple


class BaseProcessor(object):
    """A base for self-built document processors.
    """
    #: The name under which this processor is known. A simple string.
    prefix = 'base'

    metadata = {}

    #: The argparser args acceptable by this processor.
    #: This list should contain ulif.openoffice.options.Argument instances.
    args = []

    def __init__(self, options=None):
        if options is None:
            options = Options()
        if not isinstance(options, Options):
            options = Options(string_dict=options)
        self.options = options
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
        raise NotImplementedError("Please provide a process() method")

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


class MetaProcessor(BaseProcessor):
    """The meta processor handles general workflow.

    When getting certain options, it constructs a pipeline of document
    processors.

    The :class:`MetaProcessor` is a kind of processor dispatcher that
    finds, setups and calls all requested processors in the requested
    order.

    """
    #: the meta processor is named 'meta'
    prefix = 'meta'

    #: We support a ``-meta-procord`` option which stands for
    #: ``processororder``. The current default order is:
    #: ``'unzip,oocp,zip'`` which means: maybe unzip the input, then
    #: convert it into HTML and afterwards zip the results.
    args = [
        Argument('-meta-procord', '--meta-processor-order',
                 default=string_to_stringtuple(DEFAULT_PROCORDER),
                 type=processor_order,
                 help='Comma-separated list of processors to run. '
                 'Default: "%s"' % DEFAULT_PROCORDER,
                 metavar='PROC_LIST',
                 ),
        ]

    @property
    def avail_procs(self):
        return get_entry_points('ulif.openoffice.processors')

    def __init__(self, options={}):
        from ulif.openoffice.options import Options
        if not isinstance(options, Options):
            options = Options(string_dict=options)
        self.all_options = options
        self.options = options
        self.metadata = {}
        return

    def process(self, input=None, metadata={'error': False}):
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
            output, metadata = proc_instance.process(input, metadata)
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
        procs = self.avail_procs
        for proc_name in self.options['meta_processor_order']:
            result.append(procs[proc_name])
        return tuple(result)


#: Output formats supported.
#: Mapping: extension <-> format (as accepted by unoconv)
#: For oocp-out-fmt only extensions (left column) are allowed.
OUTPUT_FORMATS = {
    "txt": "text",  # text (encoded)
    "pdf": "pdf",
    "html": "html",
    "xhtml": "xhtml",
    }


class OOConvProcessor(BaseProcessor):
    """A processor that converts office docs into different formats.

    XXX: we could support far more options. See

         http://wiki.services.openoffice.org/wiki/API/Tutorials/
                PDF_export#How_to_use_it_from_OOo_Basic

         only for a list of PDF export options.
    """
    prefix = 'oocp'

    #: mapping: extension <-> format (as accepted by unoconv)
    formats = OUTPUT_FORMATS

    options = {}

    args = [
        Argument('-oocp-out-fmt', '--oocp-output-format',
                 choices=OUTPUT_FORMATS.keys(),
                 default='html',
                 help=(
                     'Output format to create via LibreOffice.'
                     'Pick from: %s' % ', '.join(OUTPUT_FORMATS.keys())),
                 metavar='FORMAT',
                 ),
        Argument('-oocp-pdf-version', '--oocp-pdf-version',
                 type=boolean, default=False, metavar='YES|NO',
                 help='Create versioned PDF (aka PDF/A)? Default: no',
                 ),
        Argument('-oocp-pdf-tagged', '--oocp-pdf-tagged',
                 type=boolean, default=False, metavar='YES|NO',
                 help='Create tagged PDF document? Default: no',
                 ),
        Argument('-oocp-host', '--oocp-hostname',
                 default='localhost',
                 help='Host to contact for LibreOffice document '
                 'conversion. Default: "localhost"'
                 ),
        Argument('-oocp-port', '--oocp-port', type=int,
                 default=2002,
                 help='Port of host to contact for LibreOffice document '
                 'conversion. Default: 2002',
                 ),
        ]

    def _get_filter_props(self):
        props = []
        if self.options['oocp_output_format'] == 'pdf':
            pdf_version = self.options['oocp_pdf_version'] and '1' or '0'
            props.append(("SelectPdfVersion", pdf_version))
            pdf_tagged = self.options['oocp_pdf_tagged'] and '1' or '0'
            props.append(("UseTaggedPDF", pdf_tagged))
        return props

    def process(self, path, metadata):
        basename = os.path.basename(path)
        src = os.path.join(
            copy_to_secure_location(path), basename)
        if os.path.isfile(path):
            path = os.path.dirname(path)
        shutil.rmtree(path)
        extension = self.options['oocp_output_format']
        filter_name = self.formats[extension]
        url = 'socket,host=%s,port=%d;urp;StarOffice.ComponentContext' % (
            self.options['oocp_hostname'], self.options['oocp_port'])

        filter_props = self._get_filter_props()
        status, result_path = convert(
            url=url,
            out_format=filter_name,
            filter_props=filter_props,
            path=src,
            out_dir=os.path.dirname(src),
            )
        metadata['oocp_status'] = status
        if status != 0:
            metadata['error'] = True
            metadata['error-descr'] = 'conversion problem'
            if os.path.isfile(src):
                src = os.path.dirname(src)
            shutil.rmtree(src)
            return None, metadata
        if extension == 'xhtml':
            extension = 'html'
        result_path = '%s.%s' % (os.path.splitext(src)[0], extension)

        # Remove input file if different from output
        if os.path.exists(src):
            if os.path.basename(result_path) != basename:
                os.unlink(src)
        return result_path, metadata


class UnzipProcessor(BaseProcessor):
    """A processor that unzips delivered files if applicable.

    The .zip file might contain only exactly one file.
    """
    prefix = 'unzip'

    supported_extensions = ['.zip', ]

    def process(self, path, metadata):
        ext = os.path.splitext(path)[1]
        if ext not in self.supported_extensions:
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

    This processor calls :command:`tidy` in a subshell. That means the
    :command:`tidy` command must be installed in system to make this
    processor work.
    """
    prefix = 'tidy'

    supported_extensions = ['.html', '.xhtml']

    def process(self, path, metadata):
        ext = os.path.splitext(path)[1]
        if ext not in self.supported_extensions:
            return path, metadata
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        src_dir = os.path.dirname(src_path)
        remove_file_dir(path)

        # Remove <SDFIELD> tags if any
        cleaned_html = rename_sdfield_tags(
            open(src_path, 'rb').read().decode('utf-8'))
        with open(src_path, 'wb') as fd:
            fd.write(cleaned_html.encode('utf-8'))

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

    args = [
        Argument('-css-cleaner-min', '--css-cleaner-minified',
                 type=boolean, default=True,
                 metavar='YES|NO',
                 help='Whether to minify generated CSS (when handling HTML) '
                 'Default: yes',
                 ),
        Argument('-css-cleaner-prettify', '--css-cleaner-prettify-html',
                 type=boolean, default=False,
                 metavar='YES|NO',
                 help='Prettify generated HTML (may lead to gaps in '
                 'rendered output) Default: no',
                 ),
    ]

    supported_extensions = ['.html', '.xhtml']

    def process(self, path, metadata):
        ext = os.path.splitext(path)[1]
        if ext not in self.supported_extensions:
            return path, metadata
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        remove_file_dir(path)

        new_html, css = extract_css(
            open(src_path, 'rb').read(), basename,
            prettify_html=self.options['css_cleaner_prettify_html'])
        css, errors = cleanup_css(
            css, minified=self.options['css_cleaner_minified'])

        css_file = os.path.splitext(src_path)[0] + '.css'
        if css is not None:
            with open(css_file, 'w') as fd:
                fd.write(css)
        with open(src_path, 'w') as fd:
            fd.write(new_html.encode('utf-8'))

        return src_path, metadata


class HTMLCleaner(BaseProcessor):
    """A processor for cleaning up HTML produced by OO.org.

    Fixes minor issues with HTML code produced by OO.org.

    This processor expects XHTML input input.
    """
    prefix = 'html_cleaner'

    args = [
        Argument('-html-cleaner-fix-head-nums',
                 '--html-cleaner-fix-heading-numbers',
                 type=boolean, default=True,
                 metavar='YES|NO',
                 help='Whether to fix heading numbers in generated HTML '
                 'Default: yes',
                 ),
        Argument('-html-cleaner-fix-img-links',
                 '--html-cleaner-fix-image-links',
                 type=boolean, default=True,
                 metavar='YES|NO',
                 help='Whether to fix heading numbers in generated HTML '
                 'Default: yes',
                 ),
        Argument('-html-cleaner-fix-sd-fields',
                 '--html-cleaner-fix-sd-fields',
                 type=boolean, default=True,
                 metavar='YES|NO',
                 help='Whether to fix SD fields in HTML generated by '
                 'LibreOffice. Default: yes',
                 ),

        ]

    supported_extensions = ['.html', '.xhtml']

    def process(self, path, metadata):
        ext = os.path.splitext(path)[1]
        if ext not in self.supported_extensions:
            return path, metadata
        basename = os.path.basename(path)
        src_path = os.path.join(
            copy_to_secure_location(path), basename)
        src_dir = os.path.dirname(src_path)
        remove_file_dir(path)

        new_html, img_name_map = cleanup_html(
            open(src_path, 'rb').read(), basename,
            fix_head_nums=self.options['html_cleaner_fix_heading_numbers'],
            fix_img_links=self.options['html_cleaner_fix_image_links'],
            fix_sdfields=self.options['html_cleaner_fix_sd_fields'],
            )
        with open(src_path, 'w') as fd:
            fd.write(new_html)
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

    def process(self, path, metadata):
        metadata.update(
            {'error-descr': 'Intentional error. Please ignore',
             'error': True})
        return None, metadata
