#! /usr/bin/env python

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

import sys, threading, time, logging, os
import pycurl

import jsonpickle
import logging, logging.handlers

import Queue
import sqlite3
import httplib, urllib2

import re

import gzip

# local
from config import *

import datetime
import rfc822

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

ABORTING_WAIT_TOO_LONG_CODE = 1
NOT_AUTHORIZED_ERROR_CODE = -1
PAGE_NOT_FOUND_ERROR_CODE = -2
HTTP_EXCEPTION_CODE = -3
URL_EXCEPTION_CODE = -4
UNKNOWN_EXCEPTION_CODE = -5

class TimelineHarvester(threading.Thread):

    def __init__(self, twitter_api, logger, label, screenname, capture_subdirname, result_queue, since_tweet_id):

        # required for threads
        super(TimelineHarvester, self).__init__()

        self.screenname = screenname
        self.label = label

        self.logger = logger

        self.logger.info("Starting thread "+self.getJobDescription())

        if since_tweet_id == "-1":
            self.since_tweet_id = -1
        else:
            self.since_tweet_id = since_tweet_id

        # self.ofilename = TIMELINE_CAPTURE_DIR+"timeline-"+screenname+".json"
        if not os.access(TIMELINE_CAPTURE_DIR+"/"+capture_subdirname, os.X_OK):
            os.mkdir(TIMELINE_CAPTURE_DIR+"/"+capture_subdirname)
            
        self.capturefilename = TIMELINE_CAPTURE_DIR+"/"+capture_subdirname+"/"+label+"-capture-"+screenname+".txt.gz"
        self.ofile = gzip.open(self.capturefilename, "a")

        # self.logfilename = TIMELINE_CAPTURE_DIR+"/"+capture_subdirname+"/log-capture-"+capture_subdirname+".log"
        # self.logfile = open(self.logfilename, "a")

        self.api = twitter_api

        self.result_queue = result_queue

        count = 0
        while True:
            # sleep_duration_between_calls = self.MaximumHitFrequency()
            (ret_code, sleep_duration_between_calls) = self.makeApiCall(self.api.MaximumHitFrequency)
        
            if ret_code == 0:
                break
            else:
                self.log(self.getJobDescription() + str(count) + ". try: MaximumHitFrequency could not be retrieved")
                time.sleep(5)
                count += 1
                # if count == 2:

                #    sys.exit()

        count = 0
        while True:
            (reset_sleep_duration, remaining_rate_limit) = self.getRemainingRateLimit()
            if reset_sleep_duration == None or remaining_rate_limit == None:
                self.log(self.getJobDescription() + str(count) + ". try: FATAL ERROR. RemainingRateLimit could not be retrieved")
                time.sleep(5)
                count += 1
                # if count == 2:

                #     sys.exit()
            else:
                break
        self.log(self.getJobDescription() + ": Remaining Rate Limit: " + str(remaining_rate_limit))

        self.sleep_duration = sleep_duration_between_calls

    def log(self, text):
        # self.logfile.write(text+"\n")
        # self.logfile.flush()
        self.logger.info(text)

    def getJobDescription(self):
        return self.label+":"+self.screenname

    def makeApiCall(self, func, *args):
        finished = False
        backoff_duration = 0
        count = 0
        ret_code = 0
        while not finished:
            try:
                if backoff_duration != 0:
                    self.log(self.getJobDescription()+ ": BACKOFF: "+str(backoff_duration)+" "+str(func))
                    time.sleep(backoff_duration)
                if len(args) != 0:
                    ret = func(*args)
                else:
                    ret = func()
                finished = True
            except TwitterError as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + ": " + str(e.message))
                if e.message == "Not authorized":
                    return [NOT_AUTHORIZED_ERROR_CODE, None]
                elif type(e.message) == type([]):
                    tmp_h = e.message[0]
                    self.log(self.getJobDescription() + ": makeApiCall: ERROR: code: " + str(tmp_h['code']) + " " + str(tmp_h['message']))
                    return [PAGE_NOT_FOUND_ERROR_CODE, None]
                if backoff_duration == 0:
                    backoff_duration = 2
                else:
                    backoff_duration = backoff_duration * 2
                if backoff_duration > 512:
                    if count == 2:
                        self.log(self.getJobDescription() + ": makeApiCall: ABORTING_WAIT_TOO_LONG")
                        return [ABORTING_WAIT_TOO_LONG_CODE, None]
                    backoff_duration = 512
                    if func.__name__ != 'Api.MaximumHitFrequency' and func.__name__ != 'Api.GetRateLimitStatus':
                        count += 1
            except httplib.HTTPException as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [HTTP_EXCEPTION_CODE, None]
            except urllib2.URLError as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [URL_EXCEPTION_CODE, None]
            except Exception as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [UNKNOWN_EXCEPTION_CODE, None]
        return [ret_code, ret]

    def GetUserTimeline(self, *args):
        if len(args) == 0:
            last_tweet_id = None
            since_tweet_id = None
        else:
            last_tweet_id = args[0]
            since_tweet_id = args[1]
            if last_tweet_id == -1:
                last_tweet_id = None
            if since_tweet_id == -1:
                since_tweet_id = None
            # else:
            #     last_tweet_id = None
        return self.api.GetUserTimeline(screen_name=self.screenname, no_cache=True, include_rts=1, count=200, max_id=last_tweet_id, since_id=since_tweet_id)

    def fetchTimeline(self):
        all_tweets = []
        page_not_found = 0
        finished = False
        first = True
        last_tweet_id = -1
        last_processed_tweet_id = -1
        n_tweets_retrieved = 0
        while not finished:
            ### make an api call
            self.log(self.getJobDescription() + ": Sleeping for "+str(self.sleep_duration)+" seconds to prevent being rate limited")
            time.sleep(self.sleep_duration)
            if not first:
                last_processed_tweet_id = last_tweet_id
                self.log(self.getJobDescription() + ": Oldest tweet id from this request: " + str(last_processed_tweet_id))
                (ret_code, tweets) = self.makeApiCall(self.GetUserTimeline, last_tweet_id, self.since_tweet_id)
                if tweets == None:
                    tweets = []
                ## if not first request, we must remove the first
                ## tweet as we have already wrote that.
                tweets = tweets[1:len(tweets)]
            else:
                first = False
                (ret_code, tweets) = self.makeApiCall(self.GetUserTimeline, last_tweet_id, self.since_tweet_id)
                if tweets == None:
                    tweets = []
                if len(tweets) > 0:
                    tweet = tweets[0]
                    since_tweet_id = tweet.id
                else:
                    since_tweet_id = -1
            ### write received tweets and determine the max_id
            if len(tweets) > 0:
                # for tweet in tweets:
                #     self.ofile.write(tweet.AsJsonString()+"\n")
                    # sys.stdout.write(".")
                    # sys.stdout.flush()
                # sys.stdout.write("\n")
                # sys.stdout.flush()
                # self.ofile.flush()
                all_tweets = all_tweets + tweets
                n_tweets_retrieved += len(tweets)
                last_tweet_id = tweets[-1].id
                if last_processed_tweet_id != -1 and last_processed_tweet_id == last_tweet_id:
                    self.log(self.getJobDescription() + ": Processed last tweet. Stopping timeline fetch.")
                    finished = True
            else:
                self.log(self.getJobDescription() + ": No tweets received.. Stopping timeline fetch.")
                finished = True
        if ret_code == PAGE_NOT_FOUND_ERROR_CODE:
            page_not_found = 1
        self.log(self.getJobDescription() + ": Retrieved "+str(n_tweets_retrieved)+" tweets.")
        for i in range(1, len(all_tweets)+1):
            tweet = all_tweets[len(all_tweets)-i]
            self.ofile.write(tweet.AsJsonString()+"\n")
        self.ofile.flush()
        self.ofile.close()
#        return [last_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found]
        return [since_tweet_id, n_tweets_retrieved, page_not_found]

    def getRemainingRateLimit(self):
        ## rate_limit_status = self.api.GetRateLimitStatus()
        (ret_code, rate_limit_status) = self.makeApiCall(self.api.GetRateLimitStatus)

        ## if there is an error
        if ret_code != 0:
            return [None, None]

        reset_time  = rate_limit_status.get('reset_time', None)
        limit = rate_limit_status.get('remaining_hits', None)

        if reset_time:
            # put the reset time into a datetime object
            reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

            # find the difference in time between now and the reset time + 1 hour
            delta = reset + datetime.timedelta(hours=1) - datetime.datetime.utcnow()

        return [int(delta.seconds), int(limit)]

    def run(self):
        result = self.fetchTimeline()
        self.result_queue.put(result)

    def progress(self, download_t, download_d, upload_t, upload_d):
        sys.stdout.write(".")

def read_userlist(filename):
    userlist = []

    f = open(filename, "r")

    line = f.readline()
    while len(line) > 0:
        line = line.strip()
        fields = [field.strip() for field in line.split(",")]
        if len(fields) > 1:
            userlist.append([fields[0], fields[1]])
        else:
            userlist.append([fields[0]])
        line = f.readline()

    f.close()

    return userlist

def update_userinfo(db_cursor, screenname, update_since_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found):
    db_cursor.execute("SELECT * FROM users WHERE screenname = ?", [screenname])
    row = db_cursor.fetchone()
    updated_at = "%s" % datetime.datetime.now()
    if row == None:
        db_cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", [screenname, since_tweet_id, n_tweets_retrieved, page_not_found, updated_at, updated_at])
    else:
        cur_n_tweets_retrieved = row['n_tweets_retrieved']
        cur_n_tweets_retrieved += n_tweets_retrieved
        if update_since_tweet_id:
            db_cursor.execute("UPDATE users SET since_tweet_id = ?, n_tweets_retrieved = ?, page_not_found = ?, updated_at = ? WHERE screenname = ?", [since_tweet_id, cur_n_tweets_retrieved, page_not_found, updated_at, screenname])
        else:
            db_cursor.execute("UPDATE users SET n_tweets_retrieved = ?, page_not_found = ?, updated_at = ? WHERE screenname = ?", [cur_n_tweets_retrieved, page_not_found, updated_at, screenname])

def get_userinfo(db_cursor, screenname):
    db_cursor.execute("SELECT * FROM users WHERE screenname = ?", [screenname])
    row = db_cursor.fetchone()
    update_required = True
    if row == None:
        return [-1, -1, update_required]
    else:
        try:
            updated_at = datetime.datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S.%f")
        except ValueError as e:
            try:
                updated_at = datetime.datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S")
            except ValueError as e2:
                ####### remove this. just for fixing an inconsistency in the database.
                tmp_str = row['updated_at']
                m = re.match("^'(.*)'$", tmp_str)
                if m:
                    tmp_str = m.group(1)
                    updated_at = datetime.datetime.strptime(tmp_str, "%Y-%m-%d %H:%M:%S.%f")
                    db_cursor.execute("UPDATE users SET created_at = ?, updated_at = ? WHERE screenname = ?", [updated_at, updated_at, screenname])
                #######
        now = datetime.datetime.now()
        if now - datetime.timedelta(days=1) < updated_at:
            update_required = False
        return [row['since_tweet_id'], row['page_not_found'], update_required]

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--projectname", help="project's name", dest="projectname")
    parser.add_argument("users_filename", help="a file with rows as ""username, label""")

    args = parser.parse_args()

    projectname = args.projectname
    if projectname == None:
        projectname = "default"
    screennames = read_userlist(args.users_filename)

    projectdir = TIMELINE_CAPTURE_DIR+"/"+projectname

    results_queue = Queue.Queue()

    if not os.access(projectdir, os.X_OK):
        os.mkdir(projectdir)

    # logging
    #logging.basicConfig(filename=projectdir+"/messages.log", format='%(asctime)s:: %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p', level=logging.DEBUG)

    logger = logging.getLogger('main_logger')
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(filename=projectdir+"/messages.log", maxBytes=10**7, backupCount=10)
    handler.setFormatter(logging.Formatter('%(asctime)s:: %(message)s', '%Y-%m-%d %I:%M:%S %p'))

    logger.addHandler(handler)

    logger.info("Logging set up.")

    logger.info("Creating the database")
    db_filename = projectdir+"/users.db"
    conn = sqlite3.connect(db_filename)
    conn.row_factory = sqlite3.Row

    db_cursor = conn.cursor()
    db_cursor.execute("CREATE TABLE IF NOT EXISTS users (screenname text PRIMARY KEY, since_tweet_id text, n_tweets_retrieved int, page_not_found int, created_at timestamp, updated_at timestamp)")

    rate_limit = 350
    estimated_max_calls_per_screenname = 17
    tolerance_duration = 5

    available_twitter_api_array = []

    for token_owner_name, access_token_key, access_token_secret in user_access_token_key_and_secrets:
        api = twitter.Api(app_consumer_key, app_consumer_secret, access_token_key, access_token_secret)
        available_twitter_api_array.append([token_owner_name, api])

    jobs = []

    n_running_jobs = 0

    n_screennames = len(screennames)

    finished = False
    while not finished:
        while len(screennames) > 0:
            if len(available_twitter_api_array) > 0:
                [screenname, label] = screennames.pop()
                (since_tweet_id, page_not_found, update_required) = get_userinfo(db_cursor, screenname)
                if page_not_found == 1:
                    logger.info("Skipping " + label + ":" + screenname + " (we got page not found error before)")
                elif not update_required:
                    logger.info("Skipping " + label + ":" + screenname + " (not expired yet)")
                else:
                    [token_owner_name, api] = available_twitter_api_array.pop()
                    t = TimelineHarvester(api, logger, label, screenname, projectname, results_queue, since_tweet_id)
                    task_start_time = time.time()
                    t.start()
                    logger.info("Thread "+token_owner_name+" => "+label+":"+screenname+" starting..")
                    logger.info("PROGRESS: " + str(len(screennames)) + "/"+str(n_screennames))
                    jobs.append([t, label, screenname, task_start_time, api, token_owner_name])
            else:
                break
    
        if len(jobs) == 0:
            finished = True
        tmp_jobs = []
        while len(jobs) > 0:
            job = jobs.pop()
            [t, label, screenname, task_start_time, api, token_owner_name] = job
            t.join(0.001)
            if not t.isAlive():
                time_elapsed = int(time.time()-task_start_time)
                logger.info("Stopping thread "+label+":"+screenname+" - (duration: "+str(time_elapsed)+" secs) - "+token_owner_name)
                sys.stdout.flush()
                result = results_queue.get(True)
                tmp_n_tweets_retrieved = result[1]
                tmp_since_tweet_id = result[0]
                if t.since_tweet_id != -1 and tmp_since_tweet_id == -1:
                    update_since_tweet_id = False
                else:
                    update_since_tweet_id = True
                update_userinfo(db_cursor, screenname, update_since_tweet_id, *result)
                conn.commit()
                available_twitter_api_array.append([token_owner_name, api])
            else:
                tmp_jobs.append(job)
        jobs = tmp_jobs
    conn.close()
