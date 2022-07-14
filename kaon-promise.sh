#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << 'EOF'
Create promises of things computing in this facility visible to other facilities.

Usage:

  kaon-promise.sh <tag>

where:
- <tag> unique name for this facility
EOF

if [ ${#*} -ge 1 ] && [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo "${hlp_msg}"
    exit
elif [ ${#*} != 1 ]; then
    echo "Invalid number of arguments"
    echo "${hlp_msg}"
    exit 1
fi

if [ x${JLAB_REMOTE_PROMISES_PATH}x == xx ]; then
    echo "kaon-get-promises.sh: error, please set up JLAB_REMOTE_PROMISES_PATH"
fi

tag="$1"

epoch="$(( `date +%s` ))"

tmpfiles="`mktemp`"
while read file crap ; do
    echo "${JLAB_REMOTE_PROMISES_PATH}/${file}@${epoch}@${tag}"
done > $tmpfiles

# Make all directories
${JLAB_REMOTE} mkdir -p `cat $tmpfiles | while read file; do dirname $file; done | sort -u`

# Do the touch
${JLAB_REMOTE} touch `cat $tmpfiles`

rm -f $tmpfiles
