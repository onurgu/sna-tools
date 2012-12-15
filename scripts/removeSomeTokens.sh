#!/bin/bash

tokens='et[Verb] ol[Verb] de[Verb] ver[Verb] yap[Verb] gel[Verb] var[Adj] yok[Adj] çık[Verb]'

cmd=''
for token in $tokens; do
    # echo $token;
    token=`echo ${token} | sed 's/\[/\\\[/g;s/\]/\\\]/g'`
    cmd=${cmd}"s/'${token}',//g;"
    # echo $cmd;
done

sed "$cmd"