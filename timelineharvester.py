#! /usr/bin/env python

import sys, threading, time, logging
import pycurl

import jsonpickle

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

class TimelineHarvester(threading.Thread):
    def __init__(self, label, screenname, sleep_duration):
        # logging
        # logging.basicConfig(file=LOGGING_DIR+"streamcatcher.log", level=logging.DEBUG )
        # self.logger= logging.getLogger( __name__ )

        # required for threads
        super(TimelineHarvester, self).__init__()

        # url = "http://api.twitter.com/1/statuses/user_timeline.json?screen_name="+screenname+"&include_rts=1&count=200"

        self.screenname = screenname
        self.label = label
        self.sleep_duration = sleep_duration

        # self.ofilename = TIMELINE_CAPTURE_DIR+"timeline-"+screenname+".json"
        self.capturefilename = TIMELINE_CAPTURE_DIR+label+"-capture-"+screenname+".txt"
        self.ofile = open(self.capturefilename, "w")

        # self.url = url

        self.apicall_count = 0

        self.abortEvent = threading.Event()

    def getApiCallCount(self):
        return self.apicall_count

    # def prepareCurl(self, url):
    #     # set libcurl options
    #     print "Fetching "+url
    #     self.curl = pycurl.Curl()
    #     self.curl.setopt(pycurl.URL, url)
    #     self.curl.setopt(pycurl.WRITEDATA, self.ofile)
    #     self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
    #     self.curl.setopt(pycurl.MAXREDIRS, 5)
    #     self.curl.setopt(pycurl.NOSIGNAL, 1)
    #     self.curl.setopt(pycurl.NOPROGRESS, 0)
    #     self.curl.setopt(pycurl.PROGRESSFUNCTION, self.progress)
    #     self.curl.perform()
    #     self.curl.close()
    #     sys.stdout.write("\n")

    def makeApiCall(self, last_tweet_id=None):
        ret_code = 0
        tweets = []
        try:
            tweets = twitter_api.GetUserTimeline(screen_name=self.screenname, include_rts=1, count=200, max_id=last_tweet_id)
        except TwitterError, e:
            print e.message
            ret_code = -1
        return [ret_code, tweets]

    def fetchTimeline(self):
        finished = False
        first = True
        last_tweet_id = -1
        last_processed_tweet_id = -1
        while not finished:
            ### make an api call
            print "Sleeping for "+str(self.sleep_duration)+" seconds to prevent being rate limited"
            time.sleep(self.sleep_duration)
            if not first:
                # if not len(last_tweet_id) > 0:
                #     print "aborting.. last_tweet_id is blank"
                #     sys.exit()
                    
                last_processed_tweet_id = last_tweet_id
                print last_processed_tweet_id
                (ret_code, tweets) = self.makeApiCall(last_tweet_id)
                self.apicall_count += 1
                # self.prepareCurl(self.url+"&max_id="+last_tweet_id)
            else:
                first = False
                #tweets = twitter_api.GetUserTimeline(screen_name=self.screenname, include_rts=1, count=200)
                (ret_code, tweets) = self.makeApiCall()
                self.apicall_count += 1
                # self.prepareCurl(self.url)
            ### write received tweets and determine the max_id
            if not first:
                tweets = tweets[1:len(tweets)]
            if len(tweets) > 0:
                for tweet in tweets:
                    self.ofile.write(tweet.AsJsonString()+"\n")
                    sys.stdout.write(".")
                    sys.stdout.flush()
                sys.stdout.write("\n")
                sys.stdout.flush()
                self.ofile.flush()
                last_tweet_id = tweets[-1].id
                if last_processed_tweet_id != -1 and last_processed_tweet_id == last_tweet_id:
                    print "Processed last tweet. Stopping timeline fetch for "+self.screenname+".."
                    finished = True
            else:
                print "No tweets received.. Stopping timeline fetch for "+self.screenname+".."
                finished = True
        self.ofile.flush()
        self.ofile.close()


                # self.ofile.write("\n")
                # self.ofile.flush()
                ### read the last tweet id
                # partial_file = open(self.ofilename, "r")
                # line = partial_file.readline()
                # last_tweet_id = ""
                # # print line
                # while len(line) > 0:
                #     try:
                #         tweet_array = jsonpickle.decode(line)
                #     except ValueError, e:
                #         print "except"
                #         print repr(e)
                #         last_tweet_id = ""
                #         line = partial_file.readline()
                #         continue
                #     if len(tweet_array) > 0 and type(tweet_array) == type([]):
                #         last_tweet = tweet_array[-1]
                #         if last_tweet.has_key("id_str"):
                #             last_tweet_id = last_tweet["id_str"]
                #             # print last_tweet_id
                #     else:
                #         print "Couldn't read a JSON Array. Probably there's a glitch.."
                #     line = partial_file.readline()
                # partial_file.close()
                # ## END: read the last tweet id.
                # if not len(last_tweet_id) > 0:
                #     finished = True

            # self.logger.info( "Read %s", url )
        # except Exception, e:
        #     # self.logger.exception( e )
        #     # print e, repr(e), e.message, e.args
        #     # callback aborted
        #     if e[0] == 42:                
        #         print "callback aborted"
        #         self.ofile.flush()
        #         self.fixCaptureFile(self.ofile)
        #         self.ofile.close()
        #     # gnutls: a tls packet with unexpected size is received.
        #     elif e[0] == 56:
        #         print "tls packet with unexpected size"
        #     else:
        #         raise
        # sys.stdout.write(".")
        # sys.stdout.flush()
        # logging.shutdown()

    # def generateCaptureFile(self):
    #     print "Generating capture file for "+self.screenname+".."
    #     ofile = open(self.ofilename, "r")
    #     capturefile = open(self.capturefilename, "w")
    #     all_tweets = []
    #     first = True
    #     line = ofile.readline()
    #     while len(line) > 0:
    #         try:
    #             tweet_array = jsonpickle.decode(line)
    #             if first:
    #                 all_tweets = all_tweets + tweet_array[:-1]
    #             else:
    #                 all_tweets = all_tweets + tweet_array[:]
    #                 first = False
    #         except ValueError, e:
    #             print repr(e)
    #             continue
    #         line = ofile.readline()
    #     ofile.close()
    #     for tweet in all_tweets:
    #         capturefile.write(jsonpickle.encode(tweet)+"\n")
    #     capturefile.close()
        

    def run(self):
        self.fetchTimeline()
        # self.generateCaptureFile()
        
    def progress(self, download_t, download_d, upload_t, upload_d):
        sys.stdout.write(".")

    def join(self, timeout=None):
        self.abortEvent.set()
        super(TimelineHarvester, self).join(timeout)

    # def fixCaptureFile(self, f):
    #     i = 0
    #     f.seek(i, 2)
    #     endpos = f.tell()
    #     # if the file is already empty
    #     if endpos == 0:
    #         return
    #     pos = endpos
    #     ch = f.read(1)
    #     print "outside: " + ch
    #     # twitter returns "\r\n" as the line end
    #     #while int(ch, 16) != int("0x0d", 16):
    #     while ch != '\r':
    #         print "inside: "+str(ch)
    #         i += 1
    #         if (pos-i) >= 0:
    #             f.seek(-1*i, 2)
    #         else:
    #             break
    #         ch = f.read(1)
    #     f.seek(-i+2, 2)
    #     f.truncate()

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

def getRemainingRateLimit():
    rate_limit_status = twitter_api.GetRateLimitStatus()
    reset_time  = rate_limit_status.get('reset_time', None)
    limit = rate_limit_status.get('remaining_hits', None)

    if reset_time:
      # put the reset time into a datetime object
      reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

      # find the difference in time between now and the reset time + 1 hour
      delta = reset + datetime.timedelta(hours=1) - datetime.datetime.utcnow()

    return [int(delta.seconds), int(limit)]

if __name__ == "__main__":

    # Initialize thread array and the file number
    #    screennames = ["onurgu"]
    # screennames = ["etemelkuran"]
    # screennames = ["cuneytozdemir"]
    # screennames = ["obenBudak","muratbardakci","ezgibasaran","ismet_berkan","AltanSan","umitalan","farukbildirici","dedeler","dsatmis","yaprakaras","selalekadak","erdilyasaroglu","metinustundag","melisalphan","serdarakinan","serdargut","saba_tumer","ahmethc","okanbayulgen","mabirand32gun","fatihaltayli","ntvspor","ayseozyilmazel","GaniMujde","ntv"]
    # screennames = ["melisalphan","serdarakinan","serdargut","saba_tumer","ahmethc","okanbayulgen","mabirand32gun","fatihaltayli","ntvspor","ayseozyilmazel","GaniMujde","ntv"]

    import argparse

    parser = argparse.ArgumentParser()
    # parser.add_argument("projectname", help="project's name")
    parser.add_argument("users_filename", help="a file with rows as ""username, label""")

    args = parser.parse_args()

    # projectname = args.projectname
    screennames = read_userlist(args.users_filename)

    rate_limit = 350
    estimated_max_calls_per_screenname = 17
    tolerance_duration = 5

    # Start one thread per URI in parallel
    # job_start_time = time.time()
    total_apicall_count = 0
    jobs = []
    for screenname, label in screennames:
        sleep_duration_between_calls = twitter_api.MaximumHitFrequency()
        (reset_sleep_duration, remaining_rate_limit) = getRemainingRateLimit()
        print "Remaining Rate Limit: " + str(remaining_rate_limit)
        t = TimelineHarvester(label, screenname, sleep_duration_between_calls)
        print "Waiting for thread "+label+":"+screenname+" to finish.."
        sys.stdout.flush()
        task_start_time = time.time()
        t.start()
        jobs.append([t, label, screenname, task_start_time])

        t.join()
        apicall_count = t.getApiCallCount()
        (reset_sleep_duration, remaining_rate_limit) = getRemainingRateLimit()
        total_apicall_count += apicall_count
        time_elapsed = int(time.time()-task_start_time)
        # job_duration = int(time.time()-job_start_time)
        print "It took "+str(time_elapsed)+" seconds."
        print "Remaining Rate Limit: " + str(remaining_rate_limit)
        if remaining_rate_limit < estimated_max_calls_per_screenname:
            print "Sleeping for "+str(reset_sleep_duration)+".."
            time.sleep(reset_sleep_duration)
            
        
        # if total_apicall_count >= rate_limit-estimated_max_calls_per_screenname:
        #     sleep_duration = 3600-job_duration+tolerance_duration
        #     print "Sleeping for "+str(sleep_duration)+".."
        #     time.sleep(sleep_duration)
        #     # resetting job start time.
        #     job_start_time = time.time()
        #     total_apicall_count = 0


        # # Wait for all threads to finish
        # for thread in threads:
        #     thread.join()
        #     t2 = time.time()
        #     print "\n** Multithreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(screennames))

    # # Start one thread per URI in sequence
    # fileno = 0
    # t1 = time.time()
    # for url in urls:
    #     f = open(str(fileno), "wb")
    #     t = StreamCatcher(url.rstrip(), f, "", "")
    #     t.start()
    #     fileno = fileno + 1
    #     t.join()
    #     f.close()
    #     t2 = time.time()
    #     print "\n** Singlethreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(urls))
