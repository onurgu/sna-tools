#!/usr/bin/python

import tokenizer

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("inputfilename", help="input filename")
parser.add_argument("outputfilename", help="output filename")

args = parser.parse_args()

ifile = open(args.inputfilename, "r")
ofile = open(args.outputfilename, "w")

line = ifile.readline()
while len(line) > 0:
    line = line.strip()
    outline = " ".join(tokenizer.tokenize(line.decode("utf8")))
    ofile.write(outline.encode("utf8") + "\n")
    line = ifile.readline()
ifile.close()
ofile.close()
