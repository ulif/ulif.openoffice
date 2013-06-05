##
## convert.py
## 
## Copyright (C) 2011, 2013 Uli Fouquet
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
A convert office docs.
"""
import logging
import shlex
import tempfile
from multiprocessing import Lock
from subprocess import Popen, PIPE

mutex = Lock()

def threadsafe(func):
    """A decorator for functions to run threadsafe.

    Acquires a mutex before running the decorated function and
    releases the mutex after the result was retrieved.
    """
    def safe_func(*args, **kw):
        result = None
        with mutex:
            result = func(*args, **kw)
        return result
    safe_func.__name__ = func.__name__
    safe_func.__dict__ = func.__dict__
    safe_func.__doc__ = func.__doc__
    return safe_func

@threadsafe
def convert(
    url="socket,host=localhost,port=2002;urp;StarOffice.ComponentContext",
    out_format = 'text', path = None, out_dir=None, filter_props = (),
    template = None, timeout = 5, doctype = 'document',
    executable='unoconv'):
    """Convert some document using `unoconv`.

    Converts the document given in `path` to `out_format` and return a
    tuple containing status (0 if everything worked okay) as well as a
    directory path holding the result document.

    The returned directory path is created freshly (unless `outdir` is
    given and exists). It is the caller's responsibility to remove
    this directory after use.

    `url` - connection string passed as `-c` parameter.

    `out_format` - destination format as string. Must be one of the
       formats provided by `unoconv --show`.

    `path` - an absolute path to the document to be converted.

    `out_dir` - an (existing) directory to place the results in. If no
      such dir is given, we create a new one.

    `filter_props` - a list of tuples containing filter setting for
      the requested conversion filter. Each tuple must contain a
      setting key and value, such as ('PageRange', '1-2'). Each filter
      setting must be applicable for the requested conversion
      filter. While, for instance, the PDF export filter provides a
      myriad of such settings, other formats probvide only few. See
      the local `unoconv` documentation for available filters.

      `filter_props` are passed to unoconv via the `-e` parameter.

    `template` - path to a template to use.

    `timeout` - seconds to wait until connections to Open/LibreOffice
      are considered failed.

    `doctype` - type of document to convert to. One of ``document``,
      ``graphics``, ``presentation``, ``spreadsheet``.

    `executable` - path to the unoconv executable to use. If none is
      given the executable is looked up in the current system path.
    """
    if not path:
        return None, []
    logger = logging.getLogger('ulif.openoffice.convert')
    new_dir = out_dir
    if new_dir is None:
        new_dir = tempfile.mkdtemp()
    logger.debug('Created dir: %s' % new_dir)
    cmd = '%s -c %s -f %s -o %s' % (
        executable, url, out_format, new_dir)
    cmd += ' -d %s' % (doctype,)
    if template is not None:
        cmd += ' -t %s' % (template,)
    for filter_prop in filter_props:
        cmd += ' -e %s=%s' % (filter_prop[0], str(filter_prop[1]))
    cmd += " " + path
    logger.info('Execute cmd: %s' % cmd)
    status, out = exec_cmd(cmd)
    logger.info('Cmd result: %s' % status)
    logger.debug('Cmd output:\n%s\n' % (out,))
    return status, new_dir

def exec_cmd(cmd):
    """Execute `cmd` in a subprocess.

    Executes `cmd` in a subprocess (w/o shell). Returns (status,
    output).  `output` contains both, stdout and stderr, as they would
    appear on the shell.
    """
    out_file = tempfile.SpooledTemporaryFile()
    args = shlex.split(cmd)
    # we could also use PIPE and p.communicate, but that seems to block
    p = Popen(args, stdout=out_file, stderr=out_file)
    status = p.wait()
    out_file.seek(0)
    out = out_file.read()
    out_file.close()
    return status, out
