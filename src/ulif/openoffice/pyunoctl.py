##
## pyunoctl.py
## Login : <uli@pu.smp.net>
## Started on  Thu Aug 27 01:50:30 2009 Uli Fouquet
## $Id$
## 
## Copyright (C) 2009 Uli Fouquet
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
"""A script controlling a server to provide some PyUNO functionality
   via network.

   The server will listen for document conversion requests on port
   2009. It requires a running OpenOffice.org server to accomplish
   this task.

   Also makes use of a cachemanager to cache document conversion
   results.

   The script is installed as executable script ``pyunoctl`` when
   using `buildout`.
"""
import logging
import logging.config
import os
import sys
from optparse import OptionParser
from ulif.openoffice.oooctl import daemonize, startstop
from ulif.openoffice.pyunoserver import run as run_pyunoserver
from ulif.openoffice.restserver import run as run_restserver

PY_BIN = '/usr/bin/python'
UNO_LIB_DIR = None
PIDFILE = '/tmp/pyunodaeomon.pid'

PORT = 2009
HOST = '127.0.0.1'
MODE = 'raw'

HOME = os.environ.get('HOME', None)
CACHE_DIR = '.pyunocache'


def getOptions():
    usage = "usage: %prog [options] start|fg|stop|restart|status"
    allowed_args = ['start', 'fg', 'stop', 'restart', 'status']
    default_cache_dir = HOME and os.path.join(HOME, CACHE_DIR) or None
    parser = OptionParser(usage=usage)

    parser.add_option(
        "-b", "--binarypath",
        help = "absolute path to OpenOffice.org binary. This option "
               "makes only sense when starting the daemon. Default: %s" %
        PY_BIN,
        default = PY_BIN,
        )

    parser.add_option(
        "-p", "--port",
        help = "port where the server listens. This option makes only "
               "sense when starting the daemon. Default: %s" % PORT,
        default = PORT,
        type = 'int',
        )

    parser.add_option(
        "--host",
        help = "host or IP where the server should listen. This option "
               "makes only sense when starting the daemon. Default: %s" % (
            HOST),
        default = HOST,
        )
    
    parser.add_option(
        "--pidfile",
        help = "absolute path of PID file. Default: %s" % PIDFILE,
        default = PIDFILE,
        )

    parser.add_option(
        "--stdout", metavar='FILE',
        help = "file where daemon messages should be logged. "
               "Default: /dev/null",
        default = '/dev/null',
        )

    parser.add_option(
        "--stderr", metavar='FILE',
        help = "file where daemon errors should be logged. "
               "If not set (default) stdout is used.",
        default = None,
        )

    parser.add_option(
        "--stdin", metavar='FILE',
        help = "file where daemon input is read from. "
               "Default: /dev/null",
        default = '/dev/null',
        )

    parser.add_option(
        "--cache-dir", metavar='DIR',
        help = "directory where to store cache files. "
               "Default: $HOME/.pyunocache. If no home "
               "directory exists or DIR is set to empty "
               "string, no caching will be performed.",
        default = default_cache_dir,
        )

    parser.add_option(
        "-m", "--mode", choices=['raw', 'rest'],
        help = "mode the server should start in. One of `raw`, `rest`. "
               "Makes only sense when starting the daemon. "
               "If started in raw mode, clients must operate on the "
               "same machine as the server. In rest mode a RESTful "
               "HTTP server is started that is slower than the raw server "
               "but can also be used from remote. See internal docs "
               "for different modes and their protocols. "
               "Default: %s" % (MODE,),
        default = MODE,
        )

    parser.add_option(
        "-l", "--logconf",
        help = "logging configuration file as explained in "
               "http://docs.python.org/library/logging.html. "
               "The configuration should define a logger for "
               "'ulif.openoffice.pyunoserver'. Default: None.",
        default = None,
        )
    
    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error("only one argument allowed. Use option '-h' for help.")

    if not os.path.isfile(options.binarypath):
        parser.error("no such file: %s. Use -b to set the binary path. "
                     "Use -h to see all options." % options.binarypath)

    if options.port < 1:
        parser.error("option -p: port must be 1 or greater: %s" % options.port)
        
    cmd = None
    if len(args) == 1:
        cmd = args[0]
    if cmd not in allowed_args:
        parser.error("argument must be one of %s. Use option '-h' for help." %
                     ', '.join(["'%s'" % x for x in allowed_args]))

    return (cmd, options)
    

def start(host, port, python_binary, uno_lib_dir, cache_dir, mode, logger):
    print "START PYUNO DAEMON"
    if mode == 'rest':
        run_restserver(host=host, port=port, python_binary=python_binary,
                       uno_lib_dir=uno_lib_dir, cache_dir=cache_dir,
                       logger=logger)
    elif mode == 'raw':
        run_pyunoserver(host=host, port=port, python_binary=python_binary,
                        uno_lib_dir=uno_lib_dir, cache_dir=cache_dir,
                        logger=logger)

def getLogger(logconf):
    """Get a logger.
    """
    if logconf is not None:
        logging.config.fileConfig(logconf)
        logger = logging.getLogger('ulif.openoffice.pyunoctl')
        logger.info('start logging')
        return logger
    logger = logging.getLogger('ulif.openoffice.pyunoctl')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def main(argv=sys.argv):
    """The main function.
    """
    if os.name != 'posix':
        print "This script only works on POSIX compliant machines."
        sys.exit(-1)
        
    (cmd, options) = getOptions()
    logger = getLogger(options.logconf)
    
    if cmd == 'start':
        if options.mode == 'rest':
            sys.stdout.write('startung RESTful HTTP server, ')
            sys.stdout.flush()
        else:
            sys.stdout.write('starting pyUNO conversion server, ')
            sys.stdout.flush()
            pass

    # startstop() returns only in case of 'start' or 'restart' cmd...
    startstop(stderr=options.stderr, stdout=options.stdout,
              stdin=options.stdin,
              pidfile=options.pidfile, action=cmd)

    start(options.host, options.port, options.binarypath, UNO_LIB_DIR,
          options.cache_dir, options.mode, logger)

    # This point will not be reached as start() will run in TCPserver
    # serve_forever() loop...
    
    sys.exit(0)
