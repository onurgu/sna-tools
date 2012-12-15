#!/bin/bash

import sys, re

line = sys.stdin.readline()
while len(line) > 0:
    # print line
    tokens = line.decode("utf-8").strip().split(",")
    result = tokens[0:2]
    for token in tokens[2:]:
        # print token
        if re.match("^'#.*'", token):
            result.append(token)
    output_str = ""
    for item in result[:-1]:
        output_str += item+","
    output_str += result[-1]
    print output_str.encode("utf-8")
    line = sys.stdin.readline()

