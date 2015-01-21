#!/bin/sh
PROGRESS=0
while [ $PROGRESS -lt "10" ]; do
    echo "[AGENT_MESSAGE] {\"progress\": $PROGRESS}"
    PROGRESS=`expr $PROGRESS + 1`
    sleep 1
done
exit 0