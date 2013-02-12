#!/bin/bash

source .initrc

PROJECT_NAME=$1
CLASS_LABEL=$2
TARGET_DIR=$MCP_TWITTER_ROOT/captures/timelines/capture-project-$PROJECT_NAME
COMBINED_FILE=$TARGET_DIR/$3
LAST_N_TWEETS=$4

for file in `ls $TARGET_DIR/$CLASS_LABEL-capture-* | xargs -n1 basename`; do

    echo $file;
    head -${LAST_N_TWEETS:-200} $TARGET_DIR/$file >> $COMBINED_FILE;

done
