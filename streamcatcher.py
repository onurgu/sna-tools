#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

from passwords import *

import oauth2 as oauth

import sys, threading, time, logging
import pycurl

import urllib

import os, subprocess

import pymongo

import jsonpickle

#import psycopg2

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
    def __init__(self, url, filename, postdata = {}, secrets = "", postgis_server = "", win=None):
        # logging
        # logging.basicConfig(file=LOGGING_DIR+"streamcatcher.log", level=logging.DEBUG )
        # self.logger= logging.getLogger( __name__ )

        # required for threads
        super(StreamCatcher, self).__init__()

        mongo_client = pymongo.MongoClient(mongo.hostname, mongo.port)

        self.direnaj_db = mongo_client.direnaj_db
        self.prev_buf = ''

        self.ofile_index = 1
        self.ofilenamebase = filename
        self.last_filenamechange_time = time.time()

        self.ofile = open(self.ofilenamebase + "." + str(self.ofile_index), "a+")
        # self.ifile = open(filename, "r")

        params = {
                'oauth_version': "1.0",
                'oauth_nonce': oauth.generate_nonce(),
                'oauth_timestamp': int(time.time())
        }

        for key, value in postdata.items():
                params[key] = value

        token = oauth.Token(key=access_token_key, secret=access_token_secret)
        consumer = oauth.Consumer(key=app_consumer_key, secret=app_consumer_secret)

        # Set our token/key parameters
        params['oauth_token'] = token.key
        params['oauth_consumer_key'] = consumer.key

        req = oauth.Request(method="POST", url=url, parameters=params, is_form_encoded=True)

        # Sign the request.
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        req.sign_request(signature_method, consumer, token)

        header = req.to_header(realm='Firehose')

        #        self.ofile.write(header.__str__())

    	#        header

        # set libcurl options
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.URL, url)
        # set to 0 for removing the header
        # self.curl.setopt(pycurl.HEADER, 1)
        self.curl.setopt(pycurl.HTTPHEADER, ['Authorization: ' + str(header['Authorization'])])
        # self.curl.setopt(pycurl.WRITEDATA, self.ofile)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.writefunction)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, self.progress)
        if len(secrets) == 0:
            self.curl.setopt(pycurl.USERPWD, "thbounsigmalab1:_integral")
        else:
            self.curl.setopt(pycurl.USERPWD, secrets)
        if len(postdata) != 0:
            self.curl.setopt(pycurl.POSTFIELDS, urllib.urlencode(postdata))

        self.abortEvent = threading.Event()

        self.download_list_win = win

        # if postgis_server != "":
        #     self.conn = psycopg2.connect(dbname="gis", user="ortaoyuncu", password="orta", host=postgis_server)
        # else:
        #     self.conn = None

    def writefunction(self, buf):

        print buf
        # mongo
        self.prev_buf = self.prev_buf + buf

        self.ofile.write(str(self.direnaj_db)+'\n')
        self.ofile.write(str(self.direnaj_db.tweets))
        self.ofile.flush()

        if '\r\n' in self.prev_buf:
           parts = self.prev_buf.split('\r\n')
           if len(parts) > 1:
               tmp = []
               for p in parts[0:-1]:
                   if len(p) > 0:
                       tmp.append(jsonpickle.decode(p))
               if len(tmp) > 0:
                   self.direnaj_db.tweets.insert(tmp)
               self.prev_buf = parts[-1]
           else:
               self.direnaj_db.tweets.insert(jsonpickle.decode(parts[0]))
               self.prev_buf = ''

        # end mongo

        change_file = False
        buffer_contains_crlf = False
        tmp_time = time.time()
        if (tmp_time - self.last_filenamechange_time) > 3600:
            change_file = True
            self.last_filenamechange_time = tmp_time
            buffer_contains_crlf = '\r\n' in buf

        if change_file and buffer_contains_crlf:
            parts = buf.split('\r\n')
            if len(parts) != 0:
                self.ofile.write(parts[0]+'\r\n')
            self.ofile.close()
            tmp_filename = self.ofilenamebase + "." + str(self.ofile_index)
            os.system("mv " + tmp_filename + " " + tmp_filename + ".done")
            # if self.pushToGIS:
            #     subprocess.Popen(["env" "MCP_TWITTER_ROOT="+ROOT_DIR, "python", "stats.py", "-P", tmp_filename + ".done", "results/coords-testing.csv"])
            self.ofile_index += 1
            self.ofile = open(self.ofilenamebase + "." + str(self.ofile_index), "a+")
            self.ofile.write('\r\n'.join(parts[1:]))
        else:
            self.ofile.write(buf)


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
        if self.download_list_win == None:
            return
        self.download_list_win.clear()
        if self.abortEvent.isSet():
            self.download_list_win.addstr(0, 0, "Aborted")
            self.download_list_win.refresh()
            return -1
        else:
            self.download_list_win.addstr(0, 0, "D: %d" % download_d)
            self.download_list_win.refresh()
        # current_pos = self.ifile.tell()
        # buf_data = ""
        # readchar = self.ifile.read(2)
        # while readchar != "":
        #     buf_data += readchar
        #     if readchar == '\r\n':
        #         # process the tweet
        #         self.process_tweet(buf_data)
        #         # purge the buffer
        #         buf_data = ""
        #         # then record the new beginning
        #         current_pos = self.ifile.tell()
        #     readchar = self.ifile.read(2)
        # self.ifile.seek(current_pos)

    # def process_tweet(buf):
    #     try:
    #         tweet = jsonpickle.decode(line)
    #     except ValueError, e:
    #         print repr(e)
    #     if tweet.has_key("delete") or tweet.has_key("scrub_geo") or tweet.has_key("limit"):
    #         print "unimplemented data item"
    #     else:
    #         text = unicode(tweet["text"])
    #         # print text
    #         screen_name = tweet["user"]["screen_name"]
    #         if tweet["user"].has_key("id_str"):
    #             user_id = tweet["user"]["id_str"]
    #             tweet_id = tweet["id_str"]
    #         else:
    #             user_id = str(tweet["user"]["id"])
    #             tweet_id = str(tweet["id"])
    #         tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")


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

    threads = []
# Start one thread per URI in parallel
    t1 = time.time()
    t = StreamCatcher("https://stream.twitter.com/1.1/statuses/filter.json", "test.txt.streamcatcher", {"track": "mahkeme"})
    t.start()
    threads.append(t)
    for thread in threads:
        thread.join()
        t2 = time.time()
        print "\n** Multithreading, %d seconds elapsed" % (int(t2-t1))
