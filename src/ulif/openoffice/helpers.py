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
