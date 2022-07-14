#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Return files that are being brought from tape.

Usage:

  kaon-get-files-transitioning-to-cache.sh
EOF 

if [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo ${hlp_msg}
    exit
elif [ ${#*} != 1 ]; then
    echo "Invalid number of arguments"
    echo ${hlp_msg}
    exit 1
fi

${JLAB_REMOTE} srmPendingRequest | grep -E "-> (pending|running)" | while read file crap ; do
    echo ${file#/cache/isoClover}
done
