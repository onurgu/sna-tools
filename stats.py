from config import *

import jsonpickle
import tokenizer

import re

import csv, time

import sys, argparse

import TurkishMorphology

class Stats():
    def __init__(self, ifilename, ofilename, ofilename2):
        self.ifilename = ifilename
        self.ofilename = ofilename
        self.ofilename2 = ofilename2
        self.token_freqs_dict = {}
        self.tokens_dates = []
        self.keyword_codings = {}
    
    def combineRowsByFirstField(self):
        '''
        expecting the input file to be in CSV format.
        '''
        self.inputfile = open(self.ifilename, "r")
        self.ofile = open(self.ofilename, "w")
        csvReader = csv.reader(self.inputfile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        combined_hash = dict()
        for row in csvReader:
            if len(row) == 0:
                # skip empty rows.
                continue
            firstField = row[0]
            skipThisManyFields = 3
            if combined_hash.has_key(firstField):
                combined_hash[firstField] = combined_hash[firstField] + row[skipThisManyFields:]
            else:
                combined_hash[firstField] = row[skipThisManyFields:]
        for key in combined_hash.keys():
            csvWriter.writerow([key] + combined_hash[key])

    def generateCSVByUsername(self):
        exclude_list = ["Det", "Adv", "Pron", "Conj", "Postp"]
        exclude_regs = []
        for e in exclude_list:
            exclude_regs.append(re.compile("^.*?\[%s\]$" % e))
        print len(exclude_regs)
	TurkishMorphology.load_lexicon('turkish.fst');
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
                text = unicode(tweet["text"])
                screen_name = tweet["user"]["screen_name"]
                user_id = tweet["user"]["id_str"]
                tweet_id = tweet["id_str"]
                tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
                tokens = tokenizer.tokenize(text)
                token_display = screen_name + " " + user_id + " " + tweet_id
                parsed_display = screen_name + " " + user_id + " " + tweet_id
                # parsing token by token for now. might think about parsing the whole sequence at once.
                for token in tokens:
                    token_display += " "+token
                    parses = TurkishMorphology.parse(token)
                    if not parses:
                        parsed_display += " "+token+"[Unknown]"
                        continue
                    min_neglogprob = float('inf')
                    min_parse = None
                    for p in parses:
                        (parse, neglogprob) = p
                        if neglogprob < min_neglogprob:
                            min_neglogprob = neglogprob
                            min_parse = parse
                    first_layer = min_parse.split('+')
                    second_layer = first_layer[0].split('-')
                    include_token = True
                    for exclude_reg in exclude_regs:
                        result = exclude_reg.match(second_layer[0])
                        if result:
                            include_token = False
                            break
                    if include_token:
                        parsed_display += " "+second_layer[0]
                #print token_display
                #print parsed_display
                ##csvWriter.writerow(token_display.split())
                csvWriter.writerow(parsed_display.split())
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

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-p", "--parse-json", action="store_true", dest="command")
group.add_argument("-c", "--combine-by-first-field", action="store_false", dest="command")
parser.add_argument("inputfilename")
parser.add_argument("outputfilename")
args = parser.parse_args()

if __name__ == '__main__':
    filename = args.inputfilename
    out_filename = args.outputfilename
    stats = Stats(filename, out_filename, "")
    if args.command:
        stats.generateCSVByUsername()
    else:
        stats.combineRowsByFirstField()
        
