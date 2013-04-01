import os

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

ROOT_DIR = os.environ["MCP_TWITTER_ROOT"]
DB_DIR = ROOT_DIR+"db/"
STATS_DIR = ROOT_DIR+"stats/"
LOGGING_DIR = ROOT_DIR+"log/"

CAPTURE_DIR = ROOT_DIR+"captures/"
TIMELINE_CAPTURE_DIR = CAPTURE_DIR+"timelines/"
CONFIG_DIR = ROOT_DIR+"configs/"
RESULTS_DIR = ROOT_DIR+"results/"

import passwords

ESC = chr(27)

LEXICON_FILENAME = ROOT_DIR+"data/lexicon-only-words-onur.txt"
