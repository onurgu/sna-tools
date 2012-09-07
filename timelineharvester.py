#! /usr/bin/env python

import sys, threading, time, logging, os
import pycurl

import jsonpickle
import logging

import Queue
import sqlite3

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

class TimelineHarvester(threading.Thread):

    def __init__(self, twitter_api, label, screenname, capture_subdirname, result_queue, last_tweet_id, since_tweet_id):

        # required for threads
        super(TimelineHarvester, self).__init__()

        self.screenname = screenname
        self.label = label

        logging.info("Starting thread "+self.getJobDescription())

        self.last_tweet_id = last_tweet_id
        if since_tweet_id == "-1":
            self.since_tweet_id = -1
        else:
            self.since_tweet_id = since_tweet_id

        # self.ofilename = TIMELINE_CAPTURE_DIR+"timeline-"+screenname+".json"
        if not os.access(TIMELINE_CAPTURE_DIR+"/"+capture_subdirname, os.X_OK):
            os.mkdir(TIMELINE_CAPTURE_DIR+"/"+capture_subdirname)
            
        self.capturefilename = TIMELINE_CAPTURE_DIR+"/"+capture_subdirname+"/"+label+"-capture-"+screenname+".txt"
        self.ofile = open(self.capturefilename, "a")

        self.logfilename = TIMELINE_CAPTURE_DIR+"/"+capture_subdirname+"/log-capture-"+capture_subdirname+".log"
        self.logfile = open(self.logfilename, "a")

        self.api = twitter_api

        self.result_queue = result_queue

        count = 0
        while True:
            # sleep_duration_between_calls = self.MaximumHitFrequency()
            (ret_code, sleep_duration_between_calls) = self.makeApiCall(self.api.MaximumHitFrequency)
        
            if ret_code == 0:
                break
            else:
                count += 1
                if count == 2:
                    self.log(self.getJobDescription() + "FATAL ERROR. MaximumHitFrequency could not be retrieved")
                    sys.exit()

        count = 0
        while True:
            (reset_sleep_duration, remaining_rate_limit) = self.getRemainingRateLimit()
            if reset_sleep_duration == None or remaining_rate_limit == None:
                count += 1
                if count == 2:
                    self.log(self.getJobDescription() + "FATAL ERROR. RemainingRateLimit could not be retrieved")
                    sys.exit()
            else:
                break
        self.log(self.getJobDescription() + ": Remaining Rate Limit: " + str(remaining_rate_limit))

        self.sleep_duration = sleep_duration_between_calls

    def log(self, text):
        # self.logfile.write(text+"\n")
        # self.logfile.flush()
        logging.info(text)

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
            except HTTPException as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [HTTP_EXCEPTION_CODE, None]
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
            else:
                last_tweet_id = None
        return self.api.GetUserTimeline(screen_name=self.screenname, include_rts=1, count=200, max_id=last_tweet_id, since_id=since_tweet_id)

    def fetchTimeline(self):
        page_not_found = 0
        finished = False
        first = True
        last_tweet_id = self.last_tweet_id
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
                for tweet in tweets:
                    self.ofile.write(tweet.AsJsonString()+"\n")
                    # sys.stdout.write(".")
                    # sys.stdout.flush()
                # sys.stdout.write("\n")
                # sys.stdout.flush()
                self.ofile.flush()
                n_tweets_retrieved += len(tweets)
                last_tweet_id = tweets[-1].id
                if last_processed_tweet_id != -1 and last_processed_tweet_id == last_tweet_id:
                    self.log(self.getJobDescription() + ": Processed last tweet. Stopping timeline fetch.")
                    finished = True
            else:
                self.log(self.getJobDescription() + ": No tweets received.. Stopping timeline fetch.")
                finished = True
        self.ofile.flush()
        self.ofile.close()
        if ret_code == PAGE_NOT_FOUND_ERROR_CODE:
            page_not_found = 1
        self.log(self.getJobDescription() + ": Retrieved "+str(n_tweets_retrieved)+" tweets.")
        return [last_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found]

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

def update_userinfo(db_cursor, screenname, update_since_tweet_id, last_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found):
    db_cursor.execute("SELECT * FROM users WHERE screenname = ?", [screenname])
    row = db_cursor.fetchone()
    if row == None:
        db_cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", [screenname, last_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found])
    else:
        cur_n_tweets_retrieved = row['n_tweets_retrieved']
        cur_n_tweets_retrieved += n_tweets_retrieved
        if update_since_tweet_id:
            db_cursor.execute("UPDATE users SET last_tweet_id = ?, since_tweet_id = ?, n_tweets_retrieved = ?, page_not_found = ? WHERE screenname = ?", [last_tweet_id, since_tweet_id, cur_n_tweets_retrieved, page_not_found, screenname])
        else:
            db_cursor.execute("UPDATE users SET last_tweet_id = ?, n_tweets_retrieved = ?, page_not_found = ? WHERE screenname = ?", [last_tweet_id, cur_n_tweets_retrieved, page_not_found, screenname])

def get_userinfo(db_cursor, screenname):
    db_cursor.execute("SELECT * FROM users WHERE screenname = ?", [screenname])
    row = db_cursor.fetchone()
    if row == None:
        return [-1, -1, -1]
    else:
        return [row['last_tweet_id'], row['since_tweet_id'], row['page_not_found']]

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
    logging.basicConfig(filename=projectdir+"/messages.log", format='%(asctime)s:: %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p', level=logging.DEBUG)
    # self.logger= logging.getLogger( __name__ )
    logging.info("Logging set up.")

    logging.info("Creating the database")
    db_filename = projectdir+"/users.db"
    conn = sqlite3.connect(db_filename)
    conn.row_factory = sqlite3.Row

    db_cursor = conn.cursor()
    db_cursor.execute("CREATE TABLE IF NOT EXISTS users (screenname text PRIMARY KEY, last_tweet_id text, since_tweet_id text, n_tweets_retrieved int, page_not_found int)")

    rate_limit = 350
    estimated_max_calls_per_screenname = 17
    tolerance_duration = 5

    available_twitter_api_array = []

    for token_owner_name, access_token_key, access_token_secret in user_access_token_key_and_secrets:
        api = twitter.Api(app_consumer_key, app_consumer_secret, access_token_key, access_token_secret)
        available_twitter_api_array.append([token_owner_name, api])

    jobs = []

    n_running_jobs = 0

    finished = False
    while not finished:
        while len(screennames) > 0:
            if len(available_twitter_api_array) > 0:
                [screenname, label] = screennames.pop()
                (last_tweet_id, since_tweet_id, page_not_found) = get_userinfo(db_cursor, screenname)
                if page_not_found == 1:
                    logging.info("Skipping " + label + ":" + screenname + " (we got page not found error before)")
                else:
                    [token_owner_name, api] = available_twitter_api_array.pop()
                    t = TimelineHarvester(api, label, screenname, projectname, results_queue, last_tweet_id, since_tweet_id)
                    task_start_time = time.time()
                    t.start()
                    logging.info("Thread "+token_owner_name+" => "+label+":"+screenname+" starting..")
                    sys.stdout.flush()
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
                logging.info("Stopping thread "+label+":"+screenname+" - (duration: "+str(time_elapsed)+" secs) - "+token_owner_name)
                sys.stdout.flush()
                result = results_queue.get(True)
                tmp_n_tweets_retrieved = result[2]
                tmp_since_tweet_id = result[1]
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
