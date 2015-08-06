##
## helpers.py
##
## Copyright (C) 2011, 2013, 2015 Uli Fouquet
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
Helpers for trivial jobs.
"""
import base64
import cssutils
import logging
import os
import re
import shutil
import tempfile
import zipfile
from bs4 import BeautifulSoup
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from pkg_resources import iter_entry_points
try:
    from urlparse import urlparse         # Python 2.x
except ImportError:                       # pragma: no cover
    from urllib import parse as urlparse  # Python 3.x
from six import string_types


def copytree(src, dst, symlinks=False, ignore=None):
    """Recursively copy an entire directory tree rooted at `src`. The
    destination directory, named by `dst`, might exist already; if
    not, thenit will be created as well as missing parent
    directories. Permissions and times of directories are copied with
    :func:`shutil.copystat`, individual files are copied using
    :func:`shutil.copy2`.

    If `symlinks` is true, symbolic links in the source tree are
    represented as symbolic links in the new tree; if false or
    omitted, the contents of the linked files are copied to the new
    tree.

    If ignore is given, it must be a callable that will receive as its
    arguments the directory being visited by :func:`shutil.copytree`,
    and a list of its contents, as returned by
    :func:`os.listdir`. Since :func:`copytree` is called recursively,
    the ignore callable will be called once for each directory that is
    copied. The callable must return a sequence of directory and file
    names relative to the current directory (i.e. a subset of the
    items in its second argument); these names will then be ignored in
    the copy process. :func:`shutil.ignore_patterns` can be used to
    create such a callable that ignores names based on glob-style
    patterns.

    If exception(s) occur, a :exc:`shutil.Error` is raised with a list
    of reasons.

    .. note:: This is a plain copy of the :func:`shutil.copytree`
              implementation as provided with Python >= 2.6. There is,
              however, one difference: this version will try to go on
              if the destination directory already exists.

              It is the callers responsibility to make sure that the
              `dst` directory is in a proper state for
              :func:`copytree`.
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    try:
        os.makedirs(dst)
    except os.error:
        pass
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except (shutil.Error) as why:
            errors.append((srcname, dstname, str(why)))
    try:
        shutil.copystat(src, dst)
    except WindowsError:                    # pragma: no cover
        # can't copy file access times on Windows
        pass
    except (OSError) as why:                # pragma: no cover
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)


def copy_to_secure_location(src):
    """Copy `src` to a temporay location.

    If `src` is a file, the complete directory containing this file
    will be copied. If `src` is a directory this directory will be
    copied.

    Returns the path of the newly created directory.

    To copy the filetree we use :func:`shutil.copytree` with no
    additional parameters. That means that symlinks won't be copied
    and other restrictions apply. See :func:`shutil.copytree` docs to
    check.
    """
    if os.path.isfile(src):
        src = os.path.dirname(src)
    dst = tempfile.mkdtemp()
    copytree(src, dst)
    return dst


def get_entry_points(group):
    """Get all entry point plugins registered for group `group`.

    The found entry points are returned as a dict with ``<NAME>`` as
    key and ``<PLUGIN>`` as value where ``<NAME>`` is the name under
    which the respective plugin was registered with setuptools and
    ``<PLUGIN>`` is the registered component itself.
    """
    return dict(
        [(x.name, x.load())
         for x in iter_entry_points(group=group)])


def unzip(path, dst_dir):
    """Unzip the files stored in zipfile `path` in `dst_dir`.

    `dst_dir` is the directory where all contents of the ZIP file is
    stored into.
    """
    zf = zipfile.ZipFile(path)
    # Create all dirs
    dirs = sorted([name for name in zf.namelist() if name.endswith('/')])
    for dir in dirs:
        new_dir = os.path.join(dst_dir, dir)
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
    # Create all files
    for name in zf.namelist():
        if name.endswith('/'):
            continue
        outfile = open(os.path.join(dst_dir, name), 'wb')
        outfile.write(zf.read(name))
        outfile.flush()
        outfile.close()
    zf.close()
    return


def zip(path):
    """Create a ZIP file out of `path`.

    If `path` points to a file then a ZIP archive is created with this
    file in compressed form in a newly created directory. The name of
    the created zipfile is the basename of the input file with a
    ``.zip`` extension appended.

    If `path` points to a directory then files and directories
    _inside_ this directory are added to the archive.

    Also empty directories are added although it cannot be guaranteed
    that these entries are recovered correctly later on with all tools
    and utilities on all platforms.

    .. note:: It is the callers responsibility to remove the directory
              the zipfile is created in after usage.
    """
    if not os.path.isdir(path) and not os.path.isfile(path):
        raise ValueError('Must be an existing path or directory: %s' % path)

    new_dir = tempfile.mkdtemp()
    basename = os.path.basename(path)
    new_path = os.path.join(new_dir, basename) + '.zip'
    zout = zipfile.ZipFile(new_path, 'w', zipfile.ZIP_DEFLATED)

    if os.path.isfile(path):
        zout.write(path, basename)
        zout.close()
        return new_path

    for root, dirs, files in os.walk(path):
        for dir in dirs:
            # XXX: Maybe the wrong way to store directories?
            dir_path = os.path.join(root, dir)
            arc_name = dir_path[len(path) + 1:] + '/'
            info = zipfile.ZipInfo(arc_name)
            zout.writestr(info, '')
        for file in files:
            file_path = os.path.join(root, file)
            arc_name = file_path[len(path) + 1:]
            zout.write(file_path, arc_name)
    zout.close()
    return new_path


def remove_file_dir(path):
    """Remove a directory.

    If `path` points to a file, the directory containing the file is
    removed. If `path` is a directory, this directory is removed.
    """
    if not isinstance(path, string_types):
        return
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        path = os.path.dirname(path)
    assert path not in ['/', '/tmp']  # Safety belt
    shutil.rmtree(path)
    return


RE_CSS_TAG = re.compile('(.+?)(\.?\s*){')
RE_CSS_STMT_START = re.compile('\s*(.*?{.*?)')
RE_CURLY_OPEN = re.compile('{([^ ])')
RE_CURLY_CLOSE = re.compile('([^ ])}')
RE_EMPTY_COMMENTS = re.compile('/\*\s*\*/')

RE_CDATA_MASSAGE = '(((/\*)?<!\[CDATA\[(\*/)?)((.*?)<!--)?'
RE_CDATA_MASSAGE += '(.*?)(-->(.*?))?((/\*)?]]>(\*/)?))'

MARKUP_MASSAGE = [
    (re.compile('(<[^<>]*)/>'), lambda x: x.group(1) + ' />'),
    (re.compile('<!\s+([^<>]*)>'),
     lambda x: '<!' + x.group(1) + '>')
    ]

CDATA_MASSAGE = MARKUP_MASSAGE
CDATA_MASSAGE.extend([
    (re.compile(RE_CDATA_MASSAGE, re.M + re.S),
     lambda match: match.group(7))])


def extract_css(html_input, basename='sample.html', prettify_html=False):
    """Scan `html_input` and replace all styles with single link to a CSS
    file.

    Returns tuple ``<MODIFIED_HTML>, <CSS-CODE>``.

    If the `html_input` contains any ``<style>`` tags, their content
    is aggregated and returned in ``<CSS-CODE``.

    The tags are all stripped from `html` input and replaced by a link
    to a stylesheet file named ``<basename>.css``. Any extension in
    `basename` is stripped. So ``sample.html`` as `basename` will
    result in a link to ``sample.css``. The same applies for a
    `basename` ``sample.css`` or ``sample``. The modified HTML code is
    returned as first item of the result tuple.

    If `pretify_html` is True, the generated HTML code is prettified
    by BeautifulSoup. This might result in unexpected, visible gaps in
    rendered output.
    """
    # create HTML massage that removes CDATA and HTML comments in styles
    for fix, m in CDATA_MASSAGE:
        html_input = fix.sub(m, html_input)
    soup = BeautifulSoup(html_input, 'html.parser')
    css = '\n'.join([style.text for style in soup.findAll('style')])
    if '<style>' in css:
        css = css.replace('<style>', '\n')

    # lowercase leading tag names
    css = re.sub(
        RE_CSS_TAG,
        lambda match:
        match.group(1).lower() + match.group(2) + '{', css)

    # set indent of all CSS statement lines to nil.
    css = re.sub(RE_CSS_STMT_START,
                 lambda match: '\n' + match.group(1), css)

    # insert spaces after and before curly brackets.
    css = re.sub(RE_CURLY_OPEN, lambda match: '{ ' + match.group(1), css)
    css = re.sub(RE_CURLY_CLOSE, lambda match: match.group(1) + ' }', css)
    css_name = os.path.splitext(basename)[0] + '.css'

    # Remove empty style comments
    css = re.sub(RE_EMPTY_COMMENTS, lambda match: '', css)

    if css.startswith('\n'):
        css = css[1:]

    for num, style in enumerate(soup.findAll('style')):
        if num == 0 and css != '':
            # replace first style with link to stylesheet
            # if there are any styles contained
            new_tag = soup.new_tag(
                'link', rel='stylesheet', type='text/css', href=css_name)
            style.replace_with(new_tag)
        else:
            style.extract()
    if css == '':
        css = None
    if prettify_html:
        return soup.prettify(), css
    return str(soup).decode("utf-8"), css


RE_HEAD_NUM = re.compile('(<h[1-6][^>]*>\s*)(([\d\.]+)+)([^\d])',
                         re.M + re.S)


def cleanup_html(html_input, basename,
                 fix_head_nums=True, fix_img_links=True, fix_sdfields=True):
    """Clean up HTML code.

    If `fix_head_nums` is ``True``, we look for heading contents of
    style ``1.1Heading`` where the number is not separated from the
    real heading text. In that case we wrap the heading number in a
    ``<span class="u-o-headnum"> tag.

    If `fix_img_links` is ``True`` we run
    :func:`rename_html_img_links` over the result.

    If `fix_sdfields` is ``True`` we rename all ``<sdfield>`` tags to
    ``<span>``. See :func:`rename_sdfield_tags` for details.

    Returns a tuple ``(<HTML_OUTPUT>, <IMG_NAME_MAP>)`` where
    ``<HTML_OUTPUT>`` is the modified HTML code and ``<IMG_NAME_MAP>``
    a mapping from old filenames to new ones (see
    :func:`rename_html_img_links`) for details.
    """
    img_name_map = {}
    if fix_img_links is True:
        html_input, img_name_map = rename_html_img_links(html_input, basename)
    if fix_sdfields is True:
        html_input = rename_sdfield_tags(html_input)
    if fix_head_nums is not True:
        return html_input, img_name_map
    # Wrap leading num-dots in headings in own span-tag.
    html_input = re.sub(
        RE_HEAD_NUM,
        lambda match: ''.join([
            match.group(1),
            '<span class="u-o-headnum">',
            match.group(3),
            '</span>',
            match.group(4)]),
        html_input)
    return html_input, img_name_map


def cleanup_css(css_input, minified=True):
    """Cleanup CSS code delivered in `css_input`, a string.

    Returns 2-item tuple ``(<CSS>, <ERRORS>)`` where ``<CSS>`` is the
    cleaned and minimized CSS code and ``<ERRORS>`` is a multiline
    string containing warnings and errors occured during processing
    the CSS.

    By default the ``<CSS>`` returned is minified to reduce network
    load, etc. If you want pretty non-minified output, set `minified`
    to ``False``.
    """
    # Set up a local logger for warnings and errors
    local_log = StringIO()
    handler = logging.StreamHandler(local_log)
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    handler.propagate = False
    handler.setLevel(logging.WARNING)
    logger = logging.getLogger()
    logger.addHandler(handler)

    cssutils.log.setLog(logger)
    cssutils.ser.prefs.useDefaults()
    if minified is True:
        cssutils.ser.prefs.useMinified()

    sheet = cssutils.parseString(css_input)

    local_log.flush()
    return sheet.cssText, local_log.getvalue()


def rename_html_img_links(html_input, basename):
    """Rename all ``<img>`` tag ``src`` attributes based on `basename`.

    Each `src` of each ``<img>`` tag in `html_input` is renamed to a
    new location of form ``<BASENAME>_<NUM>.<EXT>`` where
    ``<BASENAME>`` is the basename of `basename`, ``<NUM>`` a unique
    number starting with 1 (one) and ``<EXT>`` the filename extension
    of the original ``src`` file.

    For example:

    ``<img src="foo_m1234.jpeg">``

    with a `basename` ``sample.html`` will be replaced by

    ``<img src="sample_1.jpeg">``

    if this is the first ``<img>`` tag in the document.

    Returns a tuple ``<HTML_OUTPUT>, <NAME_MAP>`` where
    ``<HTML_OUTPUT>`` is the modified HTML and ``<NAME_MAP>`` is a
    dictionary with a mapping from old filenames to new ones. The
    latter can be used to rename any real files (which is not done by
    this function).

    Links to 'external' sources (http and similar) are ignored.
    """
    soup = BeautifulSoup(html_input, 'html.parser')
    img_tags = soup.findAll('img')
    img_map = {}
    num = 1
    basename = os.path.splitext(basename)[0]
    basename = basename.replace('.', '_')
    for tag in img_tags:
        src = tag.get('src', None)
        if src is None:
            continue
        if src in img_map.keys():
            # We found a link to the same image already
            tag['src'] = img_map[src]
            continue
        scheme = urlparse(src)[0]
        if scheme not in ['file', '']:
            # only handle local files
            continue
        ext = ''
        if '.' in src:
            ext = os.path.splitext(src)[1]
        new_src = unicode('%s_%s%s' % (basename, num, ext))
        num += 1
        tag['src'] = new_src
        img_map[src] = new_src
    return str(soup), img_map


RE_SDFIELD_OPEN = re.compile('<sdfield([^>]*)>', re.M + re.S + re.I)
RE_SDFIELD_CLOSE = re.compile('</sdfield>', re.M + re.S + re.I)


def rename_sdfield_tags(html_input):
    """Rename all ``<sdfield>`` tags to ``<span class="sdfield">``

    Any attributes are preserved.
    """
    html_input = re.sub(
        RE_SDFIELD_OPEN, lambda match: '<span %s%s>' % (
            'class="sdfield"', match.group(1)), html_input)
    return re.sub(
        RE_SDFIELD_CLOSE, lambda match: '</span>', html_input)


def base64url_encode(string):
    """Get a base64url encoding of string.

    base64url is regular base64 encoding with ``/`` and ``+`` in the
    result substituted by ``_`` and ``-`` respectively.

    This encoding is better suited for generating file system paths
    out of binary data.
    """
    if isinstance(string, str):
        try:
            string = string.encode("latin-1")
        except UnicodeDecodeError:
            # Python 2.x
            pass
    result = base64.urlsafe_b64encode(string)
    if not isinstance(result, str):
        result = result.decode("ascii")
    return result


def base64url_decode(string):
    """Decode the base64url encoded `string`.

    .. seealso:: base64url_encode
    """
    result = base64.urlsafe_b64decode(string)
    if not isinstance(result, str):
        # Python 3.x only.
        result = result.decode("latin-1")
    return result


def string_to_bool(string):
    """Turn string into a boolean value.

    ``yes``, ``1``, and ``true`` are considered as ``True``. ``no``,
    ``0``, and ``false`` are considered ``False``. If none of that
    applies, ``None`` is returned. The case does not matter, so you
    can use upper, lower or mixed case.

    If, by accident, you pass in a boolean value this will be returned
    unchanged.

    Other values result in ``None``.
    """
    if not isinstance(string, string_types):
        if string is True or string is False:
            return string
        return None
    if string.lower() in ['yes', '1', 'true']:
        return True
    if string.lower() in ['no', '0', 'false']:
        return False
    return None


def strict_string_to_bool(string):
    """A variant of `string_to_bool` which raises a `ValueError` if no
    valid boolean value can be parsed from `string`.
    """
    result = string_to_bool(string)
    if result is None:
        raise ValueError(
            '%s is not a valid boolean. Use "yes" or "no".' % string)
    return result


def string_to_stringtuple(string, strict=False):
    """Convert a single string into a tuple of strings.

    The input string is expected to contain comma-separated string
    values. The single values are stripped (whitespaces removed at
    beginning and ending).

       >>> string_to_stringtuple('foo, bar,baz')
       ('foo', 'bar', 'baz')

    By default empty strings (``',,,,'`` and similar) are filtered
    out.

    This function is _not_ 'strict' by default. If `strict` is set to
    ``True`` it does not accept empty strings or ``None`` as input.
    """
    if not string:
        if strict:
            raise ValueError('`string` must contain at least some string')
        else:
            return ()
    result = [x.strip() for x in string.split(',') if x]
    return tuple(result)


def filelike_cmp(file1, file2, chunksize=512):
    """Compare `file1` and `file2`.

    Returns ``True`` if both are equal, ``False`` else.

    Both, `file1` and `file2` can be paths to files or file-like
    objects already open for reading.

    If both are arguments are paths, consider using `filecmp.cmp` from
    the standard library instead.

    `chunksize` gives chunk size in bytes used during comparison.

    """
    f1 = file1
    f2 = file2
    result = True
    if isinstance(file1, string_types) or isinstance(file1, bytes):
        f1 = open(file1, 'rb')
    if isinstance(file2, string_types) or isinstance(file2, bytes):
        f2 = open(file2, 'rb')
    f1.seek(0)  # make sure we read from beginning, especially whe used
    f2.seek(0)  # in loops.
    try:
        while True:
            chunk1 = f1.read(chunksize)
            chunk2 = f2.read(chunksize)
            if chunk1 != chunk2:
                result = False
                break
            if not chunk1:
                break
    finally:
        if isinstance(file1, string_types) or isinstance(file1, bytes):
            f1.close()
        if isinstance(file2, string_types) or isinstance(file2, bytes):
            f2.close()
    return result


def write_filelike(file_obj, path, chunksize=512):
    """Write contents of `file_obj` to `path`.

    `file_obj` can be a string or some file-like object. If it is a
    file-like object, it must be opened for reading.

    Content is written in chunks of `chunksize`.
    """
    f1 = file_obj
    if isinstance(file_obj, string_types):
        f1 = StringIO(file_obj)
    f2 = open(path, 'w')
    try:
        while True:
            chunk = f1.read(512)
            if chunk:
                f2.write(chunk)
            else:
                break
    finally:
        f2.close()
    return
