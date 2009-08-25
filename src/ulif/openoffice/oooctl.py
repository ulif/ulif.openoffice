##
## ooo_handler.py
## Login : <uli@pu.smp.net>
## Started on  Fri Mar 14 14:05:51 2008 Uli Fouquet
## $Id$
## 
## Copyright (C) 2008 Uli Fouquet
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
Start/stop a locally installed OpenOffice.org server instance.

This script requires (beside an installed OOo server) a running X
server.

Many code inhere is stolen from the cookbook:

  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

Changes were made to handle whole process groups instead of single
processes.

"""
import sys
import os
import time
from signal import SIGTERM

OOO_BINARY = os.path.join(
    os.path.abspath(
        os.path.dirname(os.path.dirname(__file__))),
    'parts', 'openoffice', 'program', 'soffice')


def run(cmd):
    pass

def daemonize(stdout='/dev/null', stderr=None, stdin='/dev/null',
              pidfile=None, startmsg = 'started with pid %s' ):
    
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit first parent
            sys.exit(0) 
    except OSError, e: 
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
    except OSError, e: 
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)
        
    if (not stderr):
	stderr = stdout

    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    #pid = str(os.getpid())
    pid = str(os.getpgrp())
    sys.stderr.write("\n%s\n" % startmsg % pid)
    sys.stderr.flush()
    if pidfile: file(pidfile,'w+').write("%s\n" % pid)

    
    # Standard Ein-/Ausgaben auf die Dateien umleiten
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def startstop(stdout='/dev/null', stderr=None, stdin='/dev/null',
              pidfile='pid.txt', startmsg = 'started with pid %s',
              action='start' ):
    if action:
        try:
            pf  = file(pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
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
                  while 1:
                      #os.kill(pid,SIGTERM)
                      os.killpg(pid,SIGTERM)
                      time.sleep(1)
               except OSError, err:
                  err = str(err)
                  if err.find("No such process") > 0:
                      os.remove(pidfile)
                      if 'stop' == action:
                          sys.exit(0)
                      action = 'start'
                      pid = None
                  else:
                      print str(err)
                      sys.exit(1)
        
        if 'start' == action:
            if pid:
                mess = "Start aborted since pid file '%s' exists.\n"
                sys.stderr.write(mess % pidfile)
                sys.exit(1)

            daemonize(stdout,stderr,stdin,pidfile,startmsg)
            return

        if 'status' == action:
            if not pid:
                sys.stderr.write('Status: Stopped\n')

            else: sys.stderr.write('Status: Running (PID %s) \n'%pid)
            sys.exit(0)



def start():
    print "Starting OpenOffice.org server..."    
    cmd = "%s %s %s" % (
        OOO_BINARY,
        '"-accept=socket,host=localhost,port=2002;urp;"',
        '-headless -nologo -nofirststartwizard -norestore')
    os.system(cmd)

def stop():
    print "Bye."

def usage():
    return '''Usage: %s [start|stop|restart|status]

    Commands:

      start:  starts an OpenOffice.org server instance.

      stop:   stops an OpenOffice.org server instance.

      restart: restarts an OpenOffice.org server instance.

      status: tell status of server process.

    Without any command this help is printed.
    ''' % sys.argv[0]

def main(argv=sys.argv):
    if os.name != 'posix':
        print "This script only works on POSIX compliant machines."
        sys.exit(-1)
    if not os.path.isfile(OOO_BINARY):
        raise IOError('No such file: %s'% OOO_BINARY)
    cmd = None
    if len(argv) > 1:
        cmd = argv[1]
    if cmd == 'start':
        print "Going into background..."
        startstop(pidfile='/tmp/ooodaeomon.pid', action='start')
        start()
    elif cmd in ['stop', 'restart', 'status']:
        startstop(pidfile='/tmp/ooodaeomon.pid', action=cmd)
    elif cmd:
        print "Unknown command: %s" % cmd
        print usage()
    else:
        print usage()
    sys.exit(0)
