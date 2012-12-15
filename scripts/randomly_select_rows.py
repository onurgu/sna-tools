#!/usr/bin/python

import sys, os

import random

if len(sys.argv) < 2:
    print "you have to input a filename and a percentage in the argument list"
else:
    filename = sys.argv[1]
    percentage = float(sys.argv[2])

    #    print filename

    f = open(filename, "r")
    line_count = 0
    line = f.readline()
    while len(line) > 0:
        line_count += 1
        line = f.readline()

    # print line_count

    n_draws = int(float(line_count) * percentage)

    # print n_draws

    l = range(1, int(line_count)+1)
    random.shuffle(l)
    selected_line_numbers = l[1:n_draws]

    selected_line_numbers.sort()
    
    ### seek to the beginning of the file
    f.seek(0)

    l_index = 0
    i = 0
    line = f.readline()
    while len(line) > 0 and i < selected_line_numbers[-1]:
        i += 1
        if i == selected_line_numbers[l_index]:
            l_index += 1
            print line.strip()
        line = f.readline()

    f.close()

    
