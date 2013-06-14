#!/usr/bin/env python

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

import sys, math
import md5, yaml
import curses, curses.textpad

#from IPython.Shell import IPShellEmbed
#ipshell = IPShellEmbed()

# local
from streamcatcher import StreamCatcher
from config import *
from stats import Stats

threads = {"catchers": [],
           "statsgenerators": []}

def main():

    stdscr = curses.initscr()

    (win_maxy, win_maxx) = stdscr.getmaxyx()

    onethirds_win_width = int(math.floor(win_maxx/3))
    half_win_heigth = int(math.floor(win_maxy/2))

    begin_x = 0 ; begin_y = 0
    height = half_win_heigth ; width = onethirds_win_width
    download_win = curses.newwin(height, width, begin_y, begin_x)
    download_win.border()
    download_win.refresh()
    download_list_win = download_win.subwin(height-2, width-2, begin_y+1, begin_x+1)

    begin_x = (onethirds_win_width-1)+2 ; begin_y = 0
    height = half_win_heigth ; width = onethirds_win_width
    configs_win = curses.newwin(height, width, begin_y, begin_x)
    configs_win.border()
    configs_win.refresh()
    configs_list_win = configs_win.subwin(height-2, width-2, begin_y+1, begin_x+1)

    begin_x = 0 ; begin_y = win_maxy-1
    height = 1 ; width = win_maxx
    status_win = curses.newwin(height, width, begin_y, begin_x)

    begin_x = 0 ; begin_y = half_win_heigth+2
    height = 1 ; width = win_maxx
    input_win = curses.newwin(height, width, begin_y, begin_x)
    input_win_textbox = curses.textpad.Textbox(input_win)
    #curses.textpad.rectangle(stdscr, begin_y, begin_x, begin_y+height+1, begin_x+width+1)

    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)

    stdscr.addstr(half_win_heigth+5, 5, "MCP Fetcher. Ready.")
    stdscr.refresh()

    while 1:
        c = stdscr.getch()
        download_win.border()
        configs_win.border()
        if c == ord('q'): break  # Exit the while()
        elif c == ord('c'): stdscr.clear()  # Clear the screen
        elif c == ord('i'):
            curses.nocbreak(); stdscr.keypad(0); curses.echo()
            #ipshell()  # Start the ipython shell
            curses.noecho(); curses.cbreak(); stdscr.keypad(1)
        elif c == ord('s'):
            status_win.clear()
            status_win.addstr("Starting the fetcher for sample.json...")
            trackFilter("./configs/sample.conf", download_list_win)
            status_win.clear()
            status_win.addstr("Fetcher started. Press S to stop...")
        elif c == ord('S'):
            status_win.clear()
            status_win.addstr("Stopping the fetcher...")
            t = threads["catchers"][0][0]
            t.join()
            status_win.addstr("Stopped.")
        elif c == ord('f'):
            status_win.clear()
            status_win.addstr("Starting the fetcher for filter.json...")
            trackFilter("filter-02.conf", download_list_win)
            status_win.clear()
            status_win.addstr("Fetcher started. Press F to stop...")
        elif c == ord('n'):
            status_win.clear()
            status_win.addstr("Please input filter choices")
            conf_filename = createNewConfig(input_win, input_win_textbox, status_win)
            #filter_postdata = input_win_textbox.edit()
            trackFilter(conf_filename, download_list_win)
            status_win.clear()
            status_win.addstr("Fetcher started. Press F to stop...")
        elif c == ord('N'):
            status_win.clear()
            status_win.addstr("Please input config filename without the directory names")
            conf_filename = input_win_textbox.edit().strip()
            trackFilter(CONFIG_DIR+conf_filename, download_list_win)
            status_win.clear()
            status_win.addstr("Fetcher started. Press F to stop...")
        elif c == ord('F'):
            status_win.clear()
            status_win.addstr("Stopping the fetcher...")
            debug_fileoutput = open("debug.log", "a+")
            try:
                debug_fileoutput.write(repr(threads))
                debug_fileoutput.write(repr(threads["catchers"]))
                t = threads["catchers"][0][0]
                t.join()
            except Exception, e:
                debug_fileoutput.write(repr(e)+"\n"+e.message+"\n"+repr(e.args))
                sys.exit()
            status_win.addstr("Stopped.")
        configs_win.refresh()
        download_win.refresh()
        status_win.refresh()
        stdscr.refresh()

    curses.nocbreak(); stdscr.keypad(0); curses.echo()
    curses.endwin()

def createNewConfig(input_win, input_win_textbox, status_win):
    conf = { "type" : "filter" }
    # Sloppy hash generation, different configs may lead to the same hash code
    # due to reordering, but this is highly unlikely for our purposes.
    status_win.clear()
    status_win.addstr("Keywords to track")
    status_win.refresh()
    track_keywords = input_win_textbox.edit().strip()
    if track_keywords == "":
        conf["track_keywords"] = None
    else:
        conf["track_keywords"] = track_keywords.split(",")
    input_win.clear()

    status_win.clear()
    status_win.addstr("Usernames to follow")
    status_win.refresh()
    follow_usernames = input_win_textbox.edit().strip()
    if follow_usernames == "":
        conf["follow_usernames"] = None
    else:
        conf["follow_usernames"] = follow_usernames.split(",")
    input_win.clear()

    status_win.clear()
    status_win.addstr("locations")
    status_win.refresh()
    locations = input_win_textbox.edit().strip()
    if locations == "":
        conf["locations"] = None
    else:
        conf["locations"] = locations.split(",")
    input_win.clear()

    # after all content data
    hash_code = md5.new(yaml.dump(conf)).hexdigest()
    conf["hash_code"] = hash_code
    conf_filename = CONFIG_DIR+("filter-%s.conf" % hash_code)
    f = open(conf_filename, "w")
    yaml.dump(conf, f, default_flow_style=False)
    f.close()
    return conf_filename

def createThread(threads, requestParameters, win=None):
    (url, postdata, filename, postgis_server) = requestParameters
#    f = open(filename, "a+")
    t = StreamCatcher(url, filename, postdata, "", postgis_server, win)
    t.start()
#    threads.append((t, f))
    threads.append((t, filename))
    return t
    # later, do not forget to join and terminate these threads

def trackFilter(conf_filename, win=None):
    requestParameters = getRequestParameters(conf_filename)
    t = createThread(threads["catchers"], requestParameters, win)

def getRequestParameters(conf_filename):
    f = open(conf_filename, "r")
    conf = yaml.load(f)
    if conf.has_key("postgis_server"):
        postgis_server = conf["postgis_server"]
    else:
        postgis_server = ""
    if conf.has_key("type") and conf["type"] == "sample":
        url = "https://stream.twitter.com/1.1/statuses/sample.json"
        # leave blank for sample
        postdata = ""
        filename = CAPTURE_DIR+("sample.txt")
    elif conf.has_key("type") and conf["type"] == "filter":
        url = "https://stream.twitter.com/1.1/statuses/filter.json"
        postdata = preparePostdata(conf)
        if conf.has_key("hash_code"):
            filename = CAPTURE_DIR+("/filter-%s.txt" % conf["hash_code"])
        else:
            filename = CAPTURE_DIR+("/filter-%s.txt" % time.strftime("%Y-%m-%d-%H-%M-%S"))
    return [url, postdata, filename, postgis_server]

def preparePostdataForUserList(usernames):
    if usernames == None or len(usernames) == 0:
        return ""
    else:
        l = twitter_api.UsersLookup(screen_name=usernames)
        user_ids = [str(ll.id) for ll in l]
        return "follow="+",".join(user_ids)

def preparePostdata(conf):
    postdata = ""
    l = []
    if conf.has_key("follow_usernames"):
        l.append(preparePostdataForUserList(conf["follow_usernames"]))
    if conf.has_key("track_keywords") and conf["track_keywords"] != None and len(conf["track_keywords"]) != 0:
        l.append("track="+(",".join(conf["track_keywords"])))
    if conf.has_key("locations") and conf["locations"] != None and len(conf["locations"]) != 0:
        # l.append("locations="+",".join(conf["locations"]))
        l.append("locations="+",".join([str(x) for x in conf["locations"]]))
    postdata = "&".join(l)
    return postdata

### Stats related functions
###
def generateStatsForFile(input_filename):
    stats = Stats(input_filename, RESULTS_DIR+"cumulative-word-frequency-01.csv", RESULTS_DIR+"tokens_by_time-01.csv")
    stats.processFile()
    return stats

if __name__ == '__main__':
    print "ad"
    main()


################
################

# def getRequestParametersForFilter(postdata):
#     url = "https://stream.twitter.com/1/statuses/filter.json"
#     postdata = postdata
#     filename = DB_DIR+("filter.txt")
#     return [url, postdata, filename]

# def getRequestParametersForSample():
#     url = "https://stream.twitter.com/1/statuses/sample.json"
#     postdata = ""
#     filename = DB_DIR+("sample.txt")
#     return [url, postdata, filename]

# def getRequestParametersForSingleUser(userid):
#     url = "https://stream.twitter.com/1/statuses/filter.json"
#     postdata = "follow=%s" % userid
#     filename = DB_DIR+("%s.txt" % userid)
#     return [url, postdata, filename]

# def trackSingleUser(userid, threads):
#     requestParameters = getRequestParametersForSingleUser(userid)
#     t = createThread(threads, requestParameters)
