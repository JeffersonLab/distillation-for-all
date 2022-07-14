#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << EOF
Find files ending in .launched, get the status of the jobs, and print a line for each file created
by the jobs and the status.

Usage:

  kaon-get-slurm-status.sh <working-path>

where:
- <working-path>, base directory where to put the scripts and write the outputs.
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

# Check if SLURM tools are available and silently quit if not
which squeue || exit

slurm_log="slurm_log.txt"
slurm_lock="slurm_lock.txt"

# Find track of launched files under this directory
work="$1"

# Get the state for all jobs as two columns, job_id and status
sq="`mktemp`"
squeue -u $USER --array -o "%.30i %.2t" > $sq

# Find all tracks
jobstatus="`mktemp`"
find "$work" -name *.launched | while read i ; do
    # Get the status of the job
    status=""
    verify_file="${i%.launched}.verified"
    if [ -f $verify_file ]; then
        # The job finished and the output was verified; get the status from the verified track
        case `cat ${i%.launched}.verified` in
        success) status="local" ;;
        fail)  status="failed" ;;
        *)  status="unknown" ;;
        esac
    else
        # Get the job id
        jobid="`cat $i`"
        # Check state of the job id
        if grep "\<${jobid}\>" $sq > $jobstatus ; then
            case `cat $jobstus | awk '{print $2}'` in
            CA|F|TO) status="failed" ;;
            CD) status="finished" ;;
            R) status="running" ;;
            P) status="queued" ;;
            *) status="unknown" ;;
            esac
        else
            status="finished"
        fi

        # If the job finished, verified the job
        if [ $status == finished ]; then
            if ${i%.launched}.sh check ; then
                echo success > $verify_file
                echo success $jobid `date` >> $slurm_log
                status="local"
            else
                echo fail > $verify_file
                echo fail $jobid `date` >> $slurm_log
                status="failed"
            fi
        fi
    fi

    # Print the output files and the state
    ${i%.launched}.sh out | while read f ; do
        echo $f $status
    done
done 

# If the number of failing in the last 10 jobs is more than 5, stop submitting jobs
if [ `tail -20 | grep fail | wc -l` -ge 10 ]; then
    touch $slurm_lock
    squeue -u $USER --array -o "%.30i %.2t" > $sq
    jobids="`mktemp`"
    find "$work" -name *.launched | while read i ; do
        # Get the status of the job
        verify_file="${i%.launched}.verified"
        if [ ! -f $verify_file ]; then
            # Get the job id
            jobid="`head -1 $i`"
            # Check state of the job id
            if grep "\<${jobid}\>" $sq > $jobstatus ; then
                case `cat $jobstus | awk '{print $2}'` in
                P) echo ${jobid} ;;
                esac
            fi
        fi
    done  > $jobids
    scontrol uhold `cat $jobids`
fi
