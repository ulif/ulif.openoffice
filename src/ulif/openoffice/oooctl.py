#
# oooctl.py
#
# Copyright (C) 2008, 2013, 2015 Uli Fouquet
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
Start/stop a locally installed OpenOffice.org server instance.

It runs `unoconv -l` and monitors status.

This script is installed as executable script ``oooctl``.
"""
import os
import signal
import socket
import subprocess
import sys
import time
from optparse import OptionParser
from signal import SIGTERM

DEFAULT_BIN_PATHS = (
    '/usr/sbin/unoconv',
    '/usr/local/bin/unoconv',
    '/usr/bin/unoconv',
    )
PIDFILE = '/tmp/ooodaemon.pid'
child_pid = None


def daemonize(stdout='/dev/null', stderr=None,
              stdin='/dev/null', pidfile=None,
              startmsg='started with pid %s'):       # pragma: no cover
    """Fork and daemonize a running process.
    """
    global child_pid
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except (OSError) as e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent, print eventual PID before
            sys.exit(0)
    except (OSError) as e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    if (not stderr):
        stderr = stdout

    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    pid = str(os.getpgrp())
    sys.stderr.write("\n%s\n" % startmsg % pid)
    sys.stderr.flush()
    if pidfile:
        with open(pidfile, 'w+') as fd:
            fd.write("%s\n" % pid)

    # Redirect standard input/output streams
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def startstop(stdout='/dev/null', stderr=None, stdin='/dev/null',
              pidfile='pid.txt', startmsg='started with pid %s',
              action='start'):                        # pragma: no cover
    """Start/stop a process.
    """
    if action:
        try:
            with open(pidfile, 'r') as fd:
                pid = int(fd.read().strip())
        except IOError:
            pid = None

        if 'stop' == action or 'restart' == action:
            if not pid:
                mess = "Could not stop, pid file '%s' missing.\n"
                sys.stderr.write(mess % pidfile)
                if 'stop' == action:
                    sys.exit(1)
                action = 'start'
                pid = None
            else:
                try:
                    sys.stderr.write("stopping pid %s..." % pid)
                    while 1:
                        os.killpg(pid, SIGTERM)
                        time.sleep(1)
                except (OSError) as err:
                    err = str(err)
                    if err.find("No such process") > 0:
                        os.remove(pidfile)
                        sys.stderr.write(" done.\n")
                        if 'stop' == action:
                            sys.exit(0)
                        action = 'start'
                        pid = None
                    else:
                        print(str(err))
                        sys.exit(1)

        if 'start' == action:
            if pid:
                mess = "Start aborted since pid file '%s' exists.\n"
                sys.stderr.write(mess % pidfile)
                sys.exit(1)

            sys.stderr.write("going into background...")
            daemonize(stdout, stderr, stdin, pidfile, startmsg)
            return

        if 'fg' == action:
            if pid:
                mess = "Start aborted since pid file '%s' exists.\n"
                sys.stderr.write(mess % pidfile)
                sys.exit(1)
            sys.stderr.write("started.\n")
            return

        if 'status' == action:
            if not pid:
                sys.stderr.write('Status: Not running\n')
            else:
                sys.stderr.write('Status: Running (PID %s) \n' % pid)
            sys.exit(0)


def start(binarypath, foreground=False):               # pragma: no cover
    """Start an instance of OpenOffice.org server on port 2002.
    """
    cmd = "%s -l" % (binarypath,)
    if not foreground:
        result = os.system(cmd)
        return result

    proc = subprocess.Popen(
        ['sh %s' % cmd],
        shell=True,
        close_fds=True,
        preexec_fn=os.setsid,
    )
    global child_pid
    child_pid = proc.pid
    return child_pid


def get_options(argv=sys.argv):
    usage = "usage: %prog [options] start|fg|stop|restart|status"
    allowed_args = ['start', 'stop', 'restart', 'status', 'fg']
    parser = OptionParser(usage=usage)

    parser.add_option(
        "-b", "--binarypath",
        help="absolute path to unoconv executable. This "
             "option makes only sense if starting the daemon. Default "
             "paths looked up: %s" %
        (', '.join(DEFAULT_BIN_PATHS)),
        )

    parser.add_option(
        "-p", "--pidfile",
        help="absolute path of PID file. Default: %s" % PIDFILE,
        default=PIDFILE,
        )

    parser.add_option(
        "--stdout", metavar='FILE',
        help="file where daemon messages should be logged. "
             "Default: /dev/null",
        default='/dev/null',
        )

    parser.add_option(
        "--stderr", metavar='FILE',
        help="file where daemon errors should be logged. "
             "If not set (default) stdout is used.",
        default=None,
        )

    parser.add_option(
        "--stdin", metavar='FILE',
        help="file where daemon input is read from. "
             "Default: /dev/null",
        default='/dev/null',
        )

    (options, args) = parser.parse_args(args=argv[1:])

    if len(args) > 1:
        parser.error("only one argument allowed. Use option '-h' for help.")

    if options.binarypath is None:
        for path in DEFAULT_BIN_PATHS:
            if os.path.isfile(path):
                options.binarypath = path
    if options.binarypath is None:  # pragma: no cover
        parser.error("cannot find a valid path to soffice binary. "
                     "Use -b to set a valid path. Use -h to see all "
                     "options.")
    if not os.path.isfile(options.binarypath):
        parser.error("no such file: %s. Use -b to set the binary path. "
                     "Use -h to see all options." % options.binarypath)

    cmd = None
    if len(args) == 1:
        cmd = args[0]
    if cmd not in allowed_args:
        parser.error("argument must be one of %s. Use option '-h' for help." %
                     ', '.join(["'%s'" % x for x in allowed_args]))
    return (cmd, options)


def signal_handler(signal, frame):                      # pragma: no cover
    print("Received SIGINT.")
    print("Stopping OpenOffice.org server.")
    global child_pid
    if child_pid is not None:
        os.killpg(child_pid, SIGTERM)
        time.sleep(1)
    sys.exit(0)


def check_port(host, port):
    """Returns True if the port is open, False otherwise.

    This function is non-blocking.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    target = socket.gethostbyname(host)
    result = sock.connect_ex((target, port))
    if result == 0:                                     # pragma: no cover
        sock.close()
        return True
    return False                                        # pragma: no cover


def wait_for_startup(host, port):                       # pragma: no cover
    while not check_port(host, port):
        time.sleep(1)
    return


def main(argv=sys.argv):                                # pragma: no cover
    """Main script to start/stop an OOo server.

    This function is called when calling ``bin/oooctl``.
    """
    if os.name != 'posix':
        print("This script only works on POSIX compliant machines.")
        sys.exit(-1)

    (cmd, options) = get_options(argv=argv)

    if cmd in ['start', 'fg']:
        sys.stdout.write('starting OpenOffice.org server, ')
        sys.stdout.flush()

    if cmd == 'fg':
        if check_port('localhost', 2002):
            mess = "start aborted!\n"
            mess += "Start aborted since the server seems to be running.\n"
            sys.stderr.write(mess)
            sys.exit(1)

    # startstop() returns only in case of 'start', 'fg', or 'restart' cmd...
    startstop(stderr=options.stderr, stdout=options.stdout,
              stdin=options.stdin,
              pidfile=options.pidfile, action=cmd)

    if cmd == 'fg':
        signal.signal(signal.SIGINT, signal_handler)
        print("Installed signal handler for SIGINT (CTRL-C)")

    start(options.binarypath, foreground=(cmd == 'fg'))

    wait_for_startup('localhost', 2002)
    while True:
        # Check for running server and restart when it is down...
        if not check_port('localhost', 2002):
            print("openoffice.org/libreoffice server seems to be down.")
            print("restarting...")
            start(options.binarypath)
            wait_for_startup('localhost', 2002)
            print("restarted.")
        time.sleep(1)


if __name__ == '__main__':                              # pragma: no cover
    main(argv=sys.argv)
