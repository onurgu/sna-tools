import os

import twitter

ROOT_DIR = os.environ["MCP_TWITTER_ROOT"]
DB_DIR = ROOT_DIR+"db/"
STATS_DIR = ROOT_DIR+"stats/"
LOGGING_DIR = ROOT_DIR+"log/"

CAPTURE_DIR = ROOT_DIR+"captures/"
CONFIG_DIR = ROOT_DIR+"configs/"
RESULTS_DIR = ROOT_DIR+"results/"

twitter_api = twitter.Api(consumer_key='BHyVvosqVGgMMa11f8zg', consumer_secret='ESG5Vy3YJET1YHW5QuLbgLPdvW2H1x1Et4vULg6jVw', access_token_key='14671745-PLfNONt54V25dq1zfecpPfheGaoBrRx3iDn7qOsmQ', access_token_secret='6X5rI3MZqBXYhkg9Vgvwg2zsdNnPDTbV3BsAVwEvqc')
