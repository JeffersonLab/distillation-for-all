#
# Environ variables used by various scripts.
#
# PLEASE set these up before calling any of the scripts here!

# JLab username
export JLAB_USER=$USER
# JLab access to /mss, /cache, and node to run srmPendingRequest
# NOTE: please execute this beforehand:  ssh -f -N -o ControlMaster=yes -J $JLAB_USER@login.jlab.org -S a $JLAB_USER@qcdi1402
export JLAB_REMOTE="ssh -S a $JLAB_USER@qcdi1402"
# The id of this facility
export THIS_FACILITY="jz-gpu"
# Path in the facility to store configuration, eigenvectors, ...
export LOCAL_CACHE=${HOME}/jk_work/cache
# Path in the facility to store SLURM scripts, XML, and output
export LOCAL_RUN=$PWD/runs
# JLab's path to remote promises
export JLAB_REMOTE_PROMISES_PATH=/volatile/JLabLQCD/${JLAB_USER}/promises

# Make globus visible
export PATH="${PATH}:${HOME}/.local/bin"
