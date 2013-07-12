#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

from passwords import *

import oauth2 as oauth

import jsonpickle

import sys, threading, time, logging
import pycurl

import urllib

import os, subprocess

#import psycopg2

# local
from config import *

class TrendsCatcher(threading.Thread):
    def __init__(self, woeid=23424969, win=None):

        # required for threads
        super(TrendsCatcher, self).__init__()

        self.token = oauth.Token(key=access_token_key, secret=access_token_secret)
        self.consumer = oauth.Consumer(key=app_consumer_key, secret=app_consumer_secret)

        self.woeid = woeid
        self.abortEvent = threading.Event()

        self.win = win

    def parseTrends(self, content):
        # print content
        obj = jsonpickle.decode(content)
        # print obj
        # print obj[0]
        trends_list = obj[0]['trends']
        # for trend in trends_list:
        #        print trend['name']
        return [trend['name'].encode('utf-8') for trend in trends_list]

    def run(self):
        client = oauth.Client(self.consumer, self.token)
        resp, content = client.request('https://api.twitter.com/1.1/trends/place.json?id=' + str(self.woeid))

        # print resp
        # print content
        # print resp.status

        self.win.clear()
        self.win.border()
        i = 0
        for line in self.parseTrends(content):
            i = i + 1
            if self.win != None:
                self.win.addstr(i, 1, line)
            # print line
        self.win.refresh()

    def join(self, timeout=None):
        self.abortEvent.set()
        super(TrendsCatcher, self).join(timeout)

if __name__ == "__main__":
    # Read list of URIs from file specified on commandline
    woeid = 23424969

    # Initialize thread array and the file number
    threads = []

    # Start one thread per URI in parallel
    t1 = time.time()
    t = TrendsCatcher(woeid)
    t.start()
    threads.append(t)
    # Wait for all threads to finish
    for thread in threads:
        thread.join()
        t2 = time.time()
        print "\n** Multithreading, %d seconds elapsed" % int(t2-t1)
