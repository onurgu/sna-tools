import os

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

import twitter
from twitter import TwitterError

ROOT_DIR = os.environ["MCP_TWITTER_ROOT"]
DB_DIR = ROOT_DIR+"db/"
STATS_DIR = ROOT_DIR+"stats/"
LOGGING_DIR = ROOT_DIR+"log/"

CAPTURE_DIR = ROOT_DIR+"captures/"
TIMELINE_CAPTURE_DIR = CAPTURE_DIR+"timelines/"
CONFIG_DIR = ROOT_DIR+"configs/"
RESULTS_DIR = ROOT_DIR+"results/"

app_consumer_key = 's1uxAFKC3gHJNK98Oct5g'
app_consumer_secret = 'Ffb5oyCa9pNjy42ueQNyJWMOGZc5bX3bt8s6sRNXYCo'

user_access_token_key_and_secrets = [
["onurgu", "14671745-PLfNONt54V25dq1zfecpPfheGaoBrRx3iDn7qOsmQ","6X5rI3MZqBXYhkg9Vgvwg2zsdNnPDTbV3BsAVwEvqc"],
["thbounsigmalab1", "788884670-gbJC8v6Sh1Kc9dnrfWtYOyQPF41vKK0T0HbBwtKa","CNzaHeEN47qCwMg8gcminPFQsDwUFLfThdsY4ro12s0"],
["thbounsigmalab2", "788891532-WpAlkwLOAmT6OfJ1nLUFqlobV74FkZewX3t8u7qa","rEOIXJPtEPzLGQIlAiVTlljPW7U9sY1cgu41HAC05rU"],
["thbounsigmalab3", "789094418-saFdQZfIsNFjuepKkviqhWpK1O927asnjXWNfeLO","zV6DPIWCiN20l7tdLyNQpZTjRMHPP50POOXO9Eus78I"]]

twitter_api = twitter.Api(app_consumer_key, app_consumer_secret, access_token_key='14671745-PLfNONt54V25dq1zfecpPfheGaoBrRx3iDn7qOsmQ', access_token_secret='6X5rI3MZqBXYhkg9Vgvwg2zsdNnPDTbV3BsAVwEvqc')

"""

thbounsigmalab1
_integral

thbounsigmalab2
_integral

thbounsigmalab3
_integral

thbounsigmalab4
_integral



"""

ESC = chr(27)

LEXICON_FILENAME = ROOT_DIR+"data/lexicon-only-words-onur.txt"
