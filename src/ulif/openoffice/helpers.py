##
## helpers.py
## Login : <uli@pu.smp.net>
## Started on  Mon May  2 00:44:52 2011 Uli Fouquet
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
Helpers for trivial jobs.
"""
import os
import shutil
import tempfile
import zipfile
from BeautifulSoup import BeautifulSoup, Tag
from pkg_resources import iter_entry_points

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
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error, err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)

def copy_to_secure_location(src): #, symlinks=False):
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
            arc_name = dir_path[len(path)+1:] + '/'
            info = zipfile.ZipInfo(arc_name)
            zout.writestr(info, '')
        for file in files:
            file_path = os.path.join(root, file)
            arc_name = file_path[len(path)+1:]
            zout.write(file_path, arc_name)
    zout.close()
    return new_path

def remove_file_dir(path):
    """Remove a directory.

    If `path` points to a file, the directory containing the file is
    removed. If `path` is a directory, this directory is removed.
    """
    if not isinstance(path, basestring):
        return
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        path = os.path.dirname(path)
    assert path not in ['/', '/tmp'] # Safety belt
    shutil.rmtree(path)
    return


def mangle_css(line):
    line = "    " + line.strip()
    if '{' in line:
        parts = line.split('{', 1)
        line = '%s{%s' % (parts[0].lower(), parts[1])
    return line


def flatten_css(input):

    def _ok(line):
        for text in ['CDATA', '<!--', '-->', '/*']:
            if text in line:
                return False
        if len(line.strip()) == 0:
            return False
        return True

    soup = BeautifulSoup(input)

    comments = soup.findAll('style')
    styles = soup.findAll('style')

    strings = []
    for num, style in enumerate(styles):
        strings.append(style.string)
        if num > 0:
            style.extract()
    new_lines = []
    for string in strings:
        new_lines.extend(string.splitlines())

    new_content = '\n'.join(
        [mangle_css(x) for x in new_lines if _ok(x)])
    new_content = '/* <![CDATA[ */\n' + new_content + '\n   /* ]]> */'
    new_tag = Tag(soup, 'style', [('type', 'text/css')])
    new_tag.insert(0, new_content)
    styles[0].replaceWith(new_tag)

    new_soup = soup.prettify()
    soup = BeautifulSoup(new_soup)
    return soup.prettify()
