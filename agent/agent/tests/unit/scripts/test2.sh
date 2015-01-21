#!/bin/bash

echo "args = $1"

if [[ $# -ne 1 ]]; then
    echo "this script should get an argument"
    exit 0
fi

if [[ $1 == "bad_code_no_msg" ]]; then
    exit -1
fi

if [[ $1 == "good_code_no_msg" ]]; then
    exit 0
fi

if [[ $1 == "bad_code_bad_msg" ]]; then
    echo '[AGENT_MESSAGE] {"errorMsg": "error mesg", "error": 243}[AGENT_MESSAGE_END]'
    exit -1
fi

if [[ $1 == "good_code_bad_msg" ]]; then
    echo '[AGENT_MESSAGE] {"errorMsg": "error mesg", "error": 243}[AGENT_MESSAGE_END]'
    exit 0
fi

if [[ $1 == "bad_code_good_msg" ]]; then
    echo '[AGENT_MESSAGE] {"progress": 100, "result": "good result"}[AGENT_MESSAGE_END]'
    exit -1
fi

if [[ $1 == "good_code_good_msg" ]]; then
    echo '[AGENT_MESSAGE] {"progress": 100, "result": "good result"}[AGENT_MESSAGE_END]'
    exit 0
fi

if [[ $1 == "bad_code_invalid_msg" ]]; then
    echo '[AGENT_MESSAGE] {"progress": 100, "result": w4wet"erwe}[AGENT_MESSAGE_END]'
    exit -1
fi

if [[ $1 == "good_code_invalid_msg" ]]; then
    echo '[AGENT_MESSAGE] {"progress": 100, "result": w4wet"erwe}[AGENT_MESSAGE_END]'
    exit 0
fi


exit 0




