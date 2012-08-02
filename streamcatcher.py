#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id: test.py,v 1.17 2007/04/10 13:25:17 kjetilja Exp $

import sys, threading, time, logging
import pycurl

# local
from config import *

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

class StreamCatcher(threading.Thread):
    def __init__(self, url, ofile, postdata = "", secrets = "", win=None):
        # logging
        # logging.basicConfig(file=LOGGING_DIR+"streamcatcher.log", level=logging.DEBUG )
        # self.logger= logging.getLogger( __name__ )

        # required for threads
        super(StreamCatcher, self).__init__()

        # set libcurl options
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.WRITEDATA, ofile)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, self.progress)
        if len(secrets) == 0:
            self.curl.setopt(pycurl.USERPWD, "onurgu:osmantosman")
        else:
            self.curl.setopt(pycurl.USERPWD, secrets)
        if len(postdata) != 0:
            self.curl.setopt(pycurl.POSTFIELDS, postdata)

        self.abortEvent = threading.Event()

        self.download_list_win = win

        self.ofile = ofile

    def run(self):
        try:
            self.curl.perform()
            self.curl.close()
            # self.logger.info( "Read %s", url )
        except Exception, e:
            # self.logger.exception( e )
            # print e, repr(e), e.message, e.args
            # callback aborted
            if e[0] == 42:                
                print "callback aborted"
                self.ofile.flush()
                self.fixCaptureFile(self.ofile)
                self.ofile.close()
            # gnutls: a tls packet with unexpected size is received.
            elif e[0] == 56:
                print "tls packet with unexpected size"
            else:
                raise
        sys.stdout.write(".")
        sys.stdout.flush()
        # logging.shutdown()
        
    def progress(self, download_t, download_d, upload_t, upload_d):
        self.download_list_win.clear()
        if self.abortEvent.isSet():
            if self.download_list_win != None:
                self.download_list_win.addstr(0, 0, "Aborted")
            self.download_list_win.refresh()
            return -1
        else:
            if self.download_list_win != None:
                self.download_list_win.addstr(0, 0, "D: %d" % download_d)
            self.download_list_win.refresh()

    def join(self, timeout=None):
        self.abortEvent.set()
        super(StreamCatcher, self).join(timeout)

    def fixCaptureFile(self, f):
        i = 0
        f.seek(i, 2)
        endpos = f.tell()
        # if the file is already empty
        if endpos == 0:
            return
        pos = endpos
        ch = f.read(1)
        print "outside: " + ch
        # twitter returns "\r\n" as the line end
        #while int(ch, 16) != int("0x0d", 16):
        while ch != '\r':
            print "inside: "+str(ch)
            i += 1
            if (pos-i) >= 0:
                f.seek(-1*i, 2)
            else:
                break
            ch = f.read(1)
        f.seek(-i+2, 2)
        f.truncate()

if __name__ == "__main__":
    # Read list of URIs from file specified on commandline
    try:
        urls = open(sys.argv[1]).readlines()
    except IndexError:
        # No file was specified, show usage string
        print "Usage: %s <file with uris to fetch>" % sys.argv[0]
        raise SystemExit

# Initialize thread array and the file number
    threads = []
    fileno = 0

# Start one thread per URI in parallel
    t1 = time.time()
    for url in urls:
        f = open(str(fileno), "rwb")
        t = StreamCatcher(url.rstrip(), f)
        t.start()
        threads.append((t, f))
        fileno = fileno + 1
# Wait for all threads to finish
        for thread, file in threads:
            thread.join()
            file.close()
            t2 = time.time()
            print "\n** Multithreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(urls))

# Start one thread per URI in sequence
    fileno = 0
    t1 = time.time()
    for url in urls:
        f = open(str(fileno), "wb")
        t = StreamCatcher(url.rstrip(), f, "", "")
        t.start()
        fileno = fileno + 1
        t.join()
        f.close()
        t2 = time.time()
        print "\n** Singlethreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(urls))
