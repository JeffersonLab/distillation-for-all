#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << 'EOF'
Launch SLURM jobs.

Usage:

  kaon-launch-jobs.sh
EOF

if [ ${#*} -ge 1 ] && [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo "${hlp_msg}"
    exit
elif [ ${#*} != 0 ]; then
    echo "Invalid number of arguments"
    echo "${hlp_msg}"
    exit 1
fi

if [ x${LOCAL_RUN}x == xx ]; then
    echo "kaon-launch-jobs.sh: error, please set up LOCAL_RUN"
fi

# Group together all SLURM jobs with the same options
t="`mktmep`"
find ${LOCAL_RUN} -name '*.sh' | while read f ; do
    [ -f ${f%.sh}.launched ] && continue
    slurm_ops="`grep "^#KAON_BATCH" $1`"
    slurm_ops="${slurm_ops#\#KAON_BATCH }"
    slurm_ops_pack="${t}-${slurm_ops// /_}"
    [ ! -f ${slurm_ops_pack} ] && cat <<< "${slurm_ops}" > ${slurm_ops_pack}
    echo $f >> ${slurm_ops_pack} 
done

d="`date +%s`"
mkdir -p managed_jobs
k="0"
while [ -f managed_jobs/${d}-${k} ]; do $(( ++k )); done
for i in ${t}-* ; do
    slurm_ops="`head -1 $i`"
    num_jobs="`tail +2 $i | wc -l`"
    f="managed_jobs/${d}-${k}"
    cat << EOF > ${f}.sh
#!/bin/bash
#SBATCH -o ${f}_%a.out ${slurm_ops}
#SBATCH --array=1-${num_jobs}%100

`
        j="1"
        tail +2 $i | while read i; do
                echo "if [ \\\$SLURM_ARRAY_TASK_ID == $j ] ; then bash $i run ; fi"
                j="$(( j+1 ))"
        done
`
EOF

    until sbatch ${f}.sh > ${f}.launched; do sleep 60; done && sleep 2
    echo Launched bath job with $num_jobs jobs
    sbatch_job_id="`awk '/Submitted/ {print $4}' ${f}.launched`"
    j="1"
    tail +2 $i | while read job; do
            echo ${sbatch_job_id}_$j > ${job%.sh}.launched
            j="$(( j+1 ))"
    done
done
