from config import *

import jsonpickle
import tokenizer

import csv, time

class Stats():
    def __init__(self, ifilename, ofilename, ofilename2):
        self.ifilename = ifilename
        self.ofilename = ofilename
        self.ofilename2 = ofilename2
        self.token_freqs_dict = {}
        self.tokens_dates = []
        self.keyword_codings = {}
    
    def generateCSVByUsername(self):
        self.inputfile = open(self.ifilename, "r")
        self.ofile = open(self.ofilename, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        line = self.inputfile.readline()
        i = 0
        while len(line) > 0:
            i = i + 1
            try:
                tweet = jsonpickle.decode(line)
            except ValueError, e:
                print repr(e)
                line = self.inputfile.readline()
                continue
            if tweet.has_key("delete") or tweet.has_key("scrub_geo") or tweet.has_key("limit"):
                print "unimplemented data item"
            else:
                #print tweet["text"]
                text = tweet["text"]
                screen_name = tweet["user"]["screen_name"]
                user_id = tweet["user"]["id_str"]
                tweet_id = tweet["id_str"]
                tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
                tokens = tokenizer.tokenize(text)
                token_display = screen_name + " " + user_id + " " + tweet_id
                for token in tokens:
                    token_display += " "+token
                print token_display
                csvWriter.writerow(token_display.split())
            line = self.inputfile.readline()
        self.ofile.close()

    def processFile(self):
        self.inputfile = open(self.ifilename, "r") 
        line = self.inputfile.readline()
        i = 0
        while len(line) > 0:
            i = i + 1
            #print i
            try:
                tweet = jsonpickle.decode(line)
            except ValueError, e:
                print repr(e)
                line = self.inputfile.readline()
                continue
            if tweet.has_key("delete") or tweet.has_key("scrub_geo") or tweet.has_key("limit"):
                print "unimplemented data item"
            else:
                #print tweet["text"]
                text = tweet["text"]
                tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
                tokens = tokenizer.tokenize(text)
                #print tokens
                #print tokens[0]
                self.countTokens(tokens)
                self.recordTokens(tokens, tweet_w)
            line = self.inputfile.readline()
        self.writeResultsToFile()
        #print len(self.token_freqs_dict)
        self.inputfile.close()

    def writeResultsToFile(self):
        self.ofile = open(self.ofilename, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        for key in self.token_freqs_dict.keys():
            csvWriter.writerow([str(key), self.token_freqs_dict[key]])
        self.ofile.close()
        # be wise and clean this up!
        self.ofile = open(self.ofilename2, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        self.prepareKeywordCodings()
        for (token, t) in self.tokens_dates:
            row = [token, time.strftime("%Y-%m-%d-%H-%M-%S", t), self.keyword_codings[token], int(time.mktime(t))]
            csvWriter.writerow(row)
        self.ofile.close()

    def countTokens(self, tokens):
        d = self.token_freqs_dict
        for token in tokens:
            if d.has_key(token):
                d[token] += 1
            else:
                d[token] = 1

    def prepareKeywordCodings(self):
        i = 0
        for key in self.token_freqs_dict:
            print key
            if not self.keyword_codings.has_key(key):
                print i
                self.keyword_codings[key] = i
                i += 1
        return self.keyword_codings

    def recordTokens(self, tokens, t):
        for token in tokens:
            self.tokens_dates.append([token, t])

if __name__ == '__main__':
    stats = Stats(CAPTURE_DIR+'filter-gazeteciler.txt', RESULTS_DIR+'test_tweets_by_username.csv', "")
    stats.generateCSVByUsername()
