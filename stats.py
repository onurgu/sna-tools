from config import *

import jsonpickle
import tokenizer

class Stats():
    def __init__(self, ofile):
        ofile = open(STATS_DIR+ofile, "w")
        token_freqs_dict = {}
    
    def processFile(self, f):
        line = f.readline()
        i = 0
        while len(line) > 0:
            i = i + 1
            print i
            obj = jsonpickle.decode(line)
            if obj.has_key("delete") or obj.has_key("scrub_geo") or obj.has_key("limit"):
                print "unimplemented data item"
            else:
                print obj["text"]
                text = obj["text"]
                a = tokenizer.tokenize(text)
                print a
                print a[0]
            line = f.readline()
