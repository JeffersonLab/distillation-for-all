#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << 'EOF'
Get all files being promised and the facility that made the promise

Usage:

  kaon-get-promises.sh [<path> <path>...]

where:
- <path> retstrict to find promises withing the paths
EOF

if [ ${#*} -ge 1 ] && [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo "${hlp_msg}"
    exit
fi

if [ x${JLAB_REMOTE_PROMISES_PATH}x == xx ]; then
    echo "kaon-get-promises.sh: error, please set up JLAB_REMOTE_PROMISES_PATH"
fi

work="$1"

buffer="$(( 60*60*24 ))"
d="$(( `date +%s` - buffer ))"
for work in "${*}" ; do
    ${JLAB_REMOTE} bash -c "[ -d ${JLAB_REMOTE_PROMISES_PATH}/${work} ] && find ${JLAB_REMOTE_PROMISES_PATH}/${work}" | while read file crap ; do
        IFS="@" read filepath epoch promiser <<< "$file"
        [ $epoch -ge $d ] && echo $filepath $promiser
    done
done
