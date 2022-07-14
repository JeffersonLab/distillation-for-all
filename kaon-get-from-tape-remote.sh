#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << 'EOF'
Request to bring some files from tape

Usage:

  ... | kaon-get-from-tape-remote.sh
where:
- ..., the script reads a list of files to bring from standard input.
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

allfiles="`mktemp`"
for f in `cat`; do echo /cache/isoClover/$f; done > $allfiles
${JLAB_REMOTE} srmGet `cat $allfiles`
rm $allfiles
