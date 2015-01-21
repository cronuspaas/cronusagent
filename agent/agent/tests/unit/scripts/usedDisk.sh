#!/bin/bash


unamestr=`uname`
if [[ $unamestr == 'SunOS' ]]; then
    USE=$(df -kt | /usr/xpg4/bin/grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $5}' | head -1 2> /dev/null)
else
    USE=$(df -kt | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $5}' | head -1 2> /dev/null)
fi

if [[ $? == 0 ]]; then
    echo "[AGENT_MESSAGE] {\"progress\": 100, \"result\": {\"key\":\"free_disk\", \"value\":$USE}}[AGENT_MESSAGE_END]"
    exit 0
else
    echo '[AGENT_MESSAGE] {"error": 500, "errorMsg": "error occured"}[AGENT_MESSAGE_END]'
    exit -1
fi
