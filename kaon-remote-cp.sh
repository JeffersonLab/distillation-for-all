#!/bin/bash

read -r -d '' hlp_msg << EOF
Transfer all files given from the standard input from the origin globus endpoint to the
destination globus endpoint. The scripts has shortcuts for some endpoints. The path given from
standard input are relative to "local cache" at each facility.

Usage:

  ... | kaon-remote-cp.sh <origin-ep> <destination-ep>
EOF 

endpoint() {
    ep="$1"
    [ $ep == here ] && ep="${THIS_FACILITY}"
    case $1 in
    jlab)       ep="b0fca1ad-f485-4a00-8fcd-bca0b93a2a1c:~/qcd/cache/isoClover"; ;;
    frontera)   ep="142d715e-8939-11e9-b807-0a37f382de32:~/work/b6p3" ; ;;
    jz)         ep="dcb5f28c-dadf-11eb-8324-45cc1b8ccd4a:/gpfsdswork/projects/rech/ual/uie52up/ppdfs" ; ;;
    esac
    echo $ep
}

if [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo ${hlp_msg}
    exit
elif [ ${#*} != 3 ]; then
    echo "Invalid number of arguments"
    echo ${hlp_msg}
    exit 1
fi

# Get the endpoint addresses
origep="`endpoint $1`"
destep="`endpoint $2`"

# Store all input files in a temporary file
t="`mktmp`"
while read f; do
    if [ $1 == here -a ! -f ${LOCAL_CACHE}/$f ]; then
        echo The file ${$LOCAL_CACHE}/$f does not exists
        exit 1
    elif [ $1 == here -o $1 == here ] && [ ! -f ${LOCAL_CACHE}/${f}.globus-to-$2 ]; then
        echo pending $origep $destep > ${LOCAL_CACHE}/${f}.globus-to-$2
        echo $f
    elif [ -f ${LOCAL_CACHE}/${f}.globus-to-$2 ]; then
        read globus_task crap < ${LOCAL_CACHE}/${f}.globus-to-$2
        status="FAILED"
        [ $globus_task != pending ] && status="`globus task show --jq 'status' $globus_task`"
        case $status in
        *SUCCEEDED*) rm ${LOCAL_CACHE}/${f}.globus-to-$2 ;;
        *FAILED*)
            echo pending $origep $destep > ${LOCAL_CACHE}/${f}.globus-to-$2
            echo $f
            ;;
        esac
    else
        echo $f
    fi
done > $t

# Create directories in destination
cat $t | while read f ; do
    echo `dirname ${destep}/${f}`
done | sort -u | while read p ; do
    globus mkdir $p || true
done

# Split the input files in groups of 100 files at most; globus complains if there are too many
# files in a single request
split -l 100 $t ${t}_

gtask="${t}.gtask"
for tt in ${t}_* ; do
    # Launch the globus task
    cat $tt | while read f; do
        echo $f $f
    done | globus transfer $origep $destep --batch > ${gtask} || exit 1

    # Get the task id
    globus_task="`cat ${gtask} | grep "Task ID" | while read a b id; do echo $id; done`"

    # Put the globus task id in all track files
    cat $tt | while read f ; do
        echo $globus_task $origep $destep > ${LOCAL_CACHE}/${f}.globus-to-$2
    done || exit 1
done || exit 1

rm -f $t ${t}_* ${gtask}
