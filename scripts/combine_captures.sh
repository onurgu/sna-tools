#!/bin/bash

source .initrc

PROJECT_NAME=$1
TARGET_DIR=$MCP_TWITTER_ROOT/captures/timelines/capture-$PROJECT_NAME
COMBINED_FILE=$TARGET_DIR/$2
LAST_N_TWEETS=$3

for file in `ls $TARGET_DIR/* | xargs -n1 basename`; do

    echo $file;
    head -${LAST_N_TWEETS:-200} $TARGET_DIR/$file >> $COMBINED_FILE;
    # cat $file >> $2;

done
