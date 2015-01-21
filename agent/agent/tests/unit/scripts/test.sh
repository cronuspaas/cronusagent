#!/bin/sh

PROGRESS=10

trap incrementProgress 1 2

incrementProgress()
{
    PROGRESS=`expr $PROGRESS + 10`
    echo "[AGENT_MESSAGE] {\"progress\": $PROGRESS}[AGENT_MESSAGE_END]"
}


while [ $PROGRESS -lt "100" ]; do
    echo "[AGENT_MESSAGE] {\"progress\": $PROGRESS}[AGENT_MESSAGE_END]"
    sleep 0.01
done

