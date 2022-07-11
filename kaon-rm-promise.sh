#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Remove promises made by any facility.

Usage:

  kaon-rm-promise.sh
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

tag="$1"

epoch="$(( `date +%s` ))"
ssh_base="ssh -J login.jlab.org qcdi1402"

tmpfiles="`mktemp`"
while read file crap ; do
    echo "/volatile/JLabLQCD/eromero/promises/${file}@*"
done > $tmpfiles

# Remove all the promises
$ssh_base rm -f `cat $tmpfiles`

rm -f $tmpfiles
