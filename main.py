#!/usr/bin/env python

from streamcatcher import StreamCatcher

from config import *

from stats import Stats

def main():
    threads = []
    trackSample(threads)
    trackSingleUser(30631061, threads)
    print "dad"
    for t, f in threads:
        t.join()
        f.close()

def generateStatsForFile(filename):
    f = open(DB_DIR+filename, "r")
    stats = Stats("deneme")
    stats.processFile(f)

def createThread(threads, requestParameters):
    (url, postdata, filename) = requestParameters
    f = open(filename, "w")
    t = StreamCatcher(url, f, postdata)
    t.start()
    threads.append((t, f))
    return t
    # later, do not forget to join and terminate these threads

def getRequestParametersForSample():
    url = "https://stream.twitter.com/1/statuses/sample.json"
    postdata = ""
    filename = DB_DIR+("sample.txt")
    return [url, postdata, filename]

def getRequestParametersForSingleUser(userid):
    url = "https://stream.twitter.com/1/statuses/filter.json"
    postdata = "follow=%s" % userid
    filename = DB_DIR+("%s.txt" % userid)
    return [url, postdata, filename]

def trackSingleUser(userid, threads):
    requestParameters = getRequestParametersForSingleUser(userid)
    t = createThread(threads, requestParameters)

def trackSample(threads):
    requestParameters = getRequestParametersForSample()
    t = createThread(threads, requestParameters)

#if __name__ == '__main__':
#    main()
