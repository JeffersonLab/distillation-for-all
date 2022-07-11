#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Request to bring some files from tape

Usage:

  ... | kaon-get-from-tape-remote.sh
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

allfiles="`mktemp`"
cat > $allfiles
ssh -J login.jlab.org qcdi1402 srmGet `cat $allfiles`
rm $allfiles
