#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Create promises of things computing in this facility visible to other facilities.

Usage:

  kaon-promise.sh <tag>

where:
- <tag> unique name for this facility
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

tag="$1"

epoch="$(( `date +%s` ))"
ssh_base="ssh -J login.jlab.org qcdi1402"

tmpfiles="`mktemp`"
while read file crap ; do
    echo "/volatile/JLabLQCD/eromero/promises/${file}@${epoch}@${tag}"
done > $tmpfiles

# Make all directories
$ssh_base `cat $tmpfiles | while read file; do dirname $file; done | sort -u`
# Do the touch
$ssh_base touch `cat $tmpfiles`

rm -f $tmpfiles
