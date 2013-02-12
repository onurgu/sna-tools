#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

from config import *

import psycopg2

import jsonpickle
import tokenizer

import re

import csv, time

import sys, argparse

import TurkishMorphology
from turkish.deasciifier import *

from aux import emoticon

emoticon_reg = tokenizer.unicode_compile(r'(%s)' % emoticon)

def read_lexicon(f):
    lex = dict()
    line = f.readline()
    while len(line) > 0:
        word = line.strip()
        if lex.has_key(word):
            lex[word] += 1
        else:
            lex[word] = 1
        line = f.readline()
    f.close()
    return lex

alphabet = u"abcçdefgğhıijklmnoöpqrsştuüvwxyz'"
LEXICON = read_lexicon(open(LEXICON_FILENAME, "r"))

def edits1(word):
   splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
   deletes    = [a + b[1:] for a, b in splits if b]
   transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
   replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
   inserts    = [a + c + b     for a, b in splits for c in alphabet]
   tmp = set(deletes + transposes + replaces + inserts)
   result = tmp
   # result = []
   # for word in tmp:
   #     print word
       # if LEXICON.has_key(word):
       #     result.append(word)
   return result

repetition_regs = []
for letter in alphabet:
    reg = re.compile("(%s{3,})" % letter)
    repetition_regs.append([letter, reg])

def removeRepetitions(word):
    for letter, reg in repetition_regs:
        word = reg.sub(r"%s" % letter, word)
    return word

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
        line_count = getLineCount(self.inputfile)
        csvReader = csv.reader(self.inputfile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        combined_hash = dict()
        i = 0
        print "Reading.."
        for row in csvReader:
            i += 1
            print "Processing Tweet " + str(i) + " of " + str(line_count) + " tweets"
            if len(row) == 0:
                # skip empty rows.
                continue
            firstField = row[0]
            labelField = row[3]
            skipThisManyFields = 4
            key = " ".join([firstField, labelField])
            if combined_hash.has_key(key):
                combined_hash[key] = combined_hash[key] + row[skipThisManyFields:]
            else:
                combined_hash[key] = row[skipThisManyFields:]
        print "Writing.."
        for key in combined_hash.keys():
            csvWriter.writerow(key.split(" ") + combined_hash[key])

    def select_best(self, edits):
        min_neglogprob = float('inf')
        min_parse = None
        for edit in edits:
            # print edit
            parses = TurkishMorphology.parse(edit.encode("utf-8"))
            if parses:
                for p in parses:
                    (parse, neglogprob) = p
                    if neglogprob < min_neglogprob:
                        min_neglogprob = neglogprob
                        min_parse = parse
                        # print min_parse
        return min_parse

    def generateCSVByUsername(self, label=""):
        exclude_list = ["Det", "Adv", "Pron", "Conj", "Postp", "Punc"]
        exclude_regs = []
        for e in exclude_list:
            exclude_regs.append(re.compile("^.*?\[%s\]$" % e))
        # print len(exclude_regs)
	TurkishMorphology.load_lexicon('turkish.fst');
        self.inputfile = open(self.ifilename, "r")
        line_count = getLineCount(self.inputfile)
        self.ofile = open(self.ofilename, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar="'",quoting=csv.QUOTE_NONNUMERIC)
        line = self.inputfile.readline()
        i = 0
        while len(line) > 0:
            i = i + 1
            print "Processing Tweet " + str(i) + " of " + str(line_count) + " tweets"
            try:
                tweet = jsonpickle.decode(line)
            except ValueError, e:
                print repr(e)
                line = self.inputfile.readline()
                continue
            if tweet.has_key("delete") or tweet.has_key("scrub_geo") or tweet.has_key("limit"):
                print "unimplemented data item"
            else:
                text = unicode(tweet["text"])
                print text
                screen_name = tweet["user"]["screen_name"]
                if tweet["user"].has_key("id_str"):
                    user_id = tweet["user"]["id_str"]
                    tweet_id = tweet["id_str"]
                else:
                    user_id = str(tweet["user"]["id"])
                    tweet_id = str(tweet["id"])
                tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
                tokens = tokenizer.tokenize(text)
#                token_display = screen_name + " " + user_id + " " + tweet_id
                parsed_display = screen_name + " " + user_id + " " + tweet_id
                if label:
                    parsed_display = parsed_display + " " + label
                # parsing token by token for now. might think about parsing the whole sequence at once.
                for token in tokens:
                    # print token
#                    token_display += " "+token
                    if token[0] == "@":
                        parsed_display += " "+token+"[Mention]"
                        continue
                    elif token[0] == "#":
                        parsed_display += " "+token+"[Hashtag]"
                        continue
                    elif emoticon_reg.match(token):
                        parsed_display += " "+token+"[Emoticon]"
                        continue
                    elif token == "RT":
                        parsed_display += " "+token+"[RT]"
                        continue
                    parses = TurkishMorphology.parse(token.encode("utf-8"))
                    best_edit = None
                    if not parses:
                        # do not include in the results. just for one time testing.
                        # we assume that no more than two consequent letters happen in words..
                        norm_token = removeRepetitions(token)
                        best_edit = self.select_best([norm_token])
                        if not best_edit:
                            dea = Deasciifier(norm_token)
                            norm_token_deasciified = dea.convert_to_turkish()
                            best_edit = self.select_best([norm_token_deasciified])
                            if not best_edit:
                                edits = edits1(norm_token_deasciified)
                                edits = edits.union(edits1(norm_token))
                                best_edit = self.select_best(edits)
                                if not best_edit:
                                    # leave this work to the latter parts of the code.
                                    # parsed_display += " "+best_edit
                                    # else:
                                    parsed_display += " "+token+"[Unknown]"
                                    continue
                    if best_edit == None:
                        min_neglogprob = float('inf')
                        min_parse = None
                        for p in parses:
                            (parse, neglogprob) = p
                            if neglogprob < min_neglogprob:
                                min_neglogprob = neglogprob
                                min_parse = parse.decode("utf-8")
                    else:
                        min_parse = best_edit.decode("utf-8")
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
                print parsed_display
                csvWriter.writerow([p.encode("utf-8") for p in parsed_display.split()])
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

    def pushToPostGIS(self):
        postgis_server = "orta-oyuncu-server"
        conn = psycopg2.connect(database="gis", user="ortaoyuncu", password="orta", host=postgis_server)
        self.inputfile = open(self.ifilename, "r") 
        line = self.inputfile.readline()
        coords_times_list = []
        i = 0
        while len(line) > 0:
            i = i + 1
            if i % 1000 == 0:
                print i
            tmp_el = []
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
                text = unicode(tweet["text"])
                tmp_el.append(text)
                if tweet["user"].has_key("id_str"):
                    user_id = tweet["user"]["id_str"]
                    tweet_id = tweet["id_str"]
                else:
                    user_id = str(tweet["user"]["id"])
                    tweet_id = str(tweet["id"])
                screen_name = tweet["user"]["screen_name"]
                tmp_el.append(screen_name)
                tmp_el.append(user_id)
                tmp_el.append(tweet_id)
                tweet_w = time.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
                # if not (tweet_w <= end_time and tweet_w >= start_time):
                #     # print "not in range"
                #     if tweet_w > end_time:
                #         break
                #     else:
                #         continue
                tmp_el.append(tweet_w)
                coord_el = []
                if tweet.has_key("coordinates"):
                    coord = tweet["coordinates"]                
                    if coord != None and coord.has_key("type") and coord["type"] == "Point":
                        coord_el = coord["coordinates"]
                    # else:
                    #    print "not a point"
                if len(coord_el) == 0:
                    line = self.inputfile.readline()
                    continue
                tmp_el.append(coord_el)
            if len(tmp_el) != 0:
                coords_times_list.append(tmp_el)
            line = self.inputfile.readline()
        self.ofile = open(self.ofilename, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        cur = conn.cursor()
        for el in coords_times_list:
            text = unicode(el[0])
            screen_name = el[1]
            user_id = el[2]
            tweet_id = el[3]
            t = el[4]
            coords = el[5]
            csvWriter.writerow(coords + [time.strftime("%Y-%m-%d-%H-%M-%S", t), int(time.mktime(t))] + [tweet_id] + [user_id] + [screen_name] + [text.encode('utf-8')]) 
            cur.execute("INSERT INTO tweets (geom, sent_at, username, tweet_text, tweet_id, user_id) VALUES (ST_GeomFromText('POINT(%s %s)', 900913), to_timestamp(%s), %s, %s, %s, %s)", (coords[0], coords[1], int(time.mktime(t)), screen_name, text.encode('utf-8'), tweet_id.encode('utf-8'), user_id.encode('utf-8')))
        conn.commit()
        cur.close()
        conn.close()
        self.ofile.close()
        self.inputfile.close()

    def extractCoordinates(self):
        self.inputfile = open(self.ifilename, "r") 
        line = self.inputfile.readline()
        coords_times_list = []
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
                if tweet.has_key("coordinates"):
                    coord = tweet["coordinates"]
                    if coord == None:
                        print "coordinates null"
                    elif coord.has_key("type") and coord["type"] == "Point":
                        coords_times_list.append([coord["coordinates"], tweet_w])
                    else:
                        print "not a point"
            line = self.inputfile.readline()
        self.ofile = open(self.ofilename, "w")
        csvWriter = csv.writer(self.ofile, delimiter=',', quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        for el in coords_times_list:
            coords = el[0]
            t = el[1]
            csvWriter.writerow(coords + [time.strftime("%Y-%m-%d-%H-%M-%S", t), int(time.mktime(t))]) 
        self.ofile.close()
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

def getLineCount(f):
    line_count = 0
    curpos = f.tell()
    line = f.readline()
    while len(line) > 0:
        line_count += 1
        line = f.readline()
    f.seek(curpos)
    return line_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--parse-json", action="store_const", const=0, dest="command")
    group.add_argument("-c", "--combine-by-first-field", action="store_const", const=1, dest="command")
    group.add_argument("-e", "--extract-coords", action="store_const", const=2, dest="command")
    group.add_argument("-P", "--push-to-postgis", action="store_const", const=3, dest="command")
#    parser.add_argument("-s", "--start-time")
#    parser.add_argument("-S", "--end-time")
    parser.add_argument("inputfilename")
    parser.add_argument("outputfilename")
    parser.add_argument("-l", "--label")
    args = parser.parse_args()
    filename = args.inputfilename
    out_filename = args.outputfilename
    stats = Stats(filename, out_filename, "")
    
    if args.command == 0:
        if args.label:
            label = args.label
        else:
            label = ""
        stats.generateCSVByUsername(label)
    elif args.command == 1:
        stats.combineRowsByFirstField()
    elif args.command == 2:
        stats.extractCoordinates()
    elif args.command == 3:
        # start_time = time.strptime(args.start_time, "%Y-%m-%d-%H-%M-%S")
        # end_time = time.strptime(args.end_time, "%Y-%m-%d-%H-%M-%S")
        # stats.pushToPostGIS(start_time, end_time)
        stats.pushToPostGIS()
        
