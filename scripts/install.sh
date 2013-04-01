#!/bin/bash

cd lib/python-twitter;

python setup.py build
sudo python setup.py install

cd -

cd lib/python-oauth2

sudo aptitude install python-setuptools
python setup.py build
sudo python setup.py install

cd -

sudo aptitude install python-jsonpickle
sudo aptitude install python-psycopg2

# require pycurl >=7.19