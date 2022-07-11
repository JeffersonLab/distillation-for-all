#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Get all files being promised and the facility that made the promise

Usage:

  kaon-get-promises.sh <path>

where:
- <path> retstrict to find promises withing the path
EOF 

if [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo ${hlp_msg}
    exit
elif [ ${#*} != 2 ]; then
    echo "Invalid number of arguments"
    echo ${hlp_msg}
    exit 1
fi

work="$1"

buffer="$(( 60*60*24 ))"
d="$(( `date +%s` - buffer ))"
ssh -J login.jlab.org qcdi1402 bash -c "[ -d /volatile/JLabLQCD/eromero/promises/${work} ] && find /volatile/JLabLQCD/eromero/promises/${work}" | while read file crap ; do
	IFS="@" read filepath epoch promiser <<< "$file"
	[ $epoch -ge $d ] && echo $filepath $promiser
done
