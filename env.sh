#
# Environ variables used by various scripts.
#
# PLEASE set these up before calling any of the scripts here!

# JLab access to /mss, /cache, and node to run srmPendingRequest
export JLAB_REMOTE="ssh -J login.jlab.org qcdi1402"
# The id of this facility
export THIS_FACILITY="jz-gpu"
# Path in the facility to store configuration, eigenvectors, ...
export LOCAL_CACHE=/scratch/whatever
# Path in the facility to store SLURM scripts, XML, and output
export LOCAL_RUN=$PWD/runs
# JLab's path to remote promises
export JLAB_REMOTE_PROMISES_PATH=/volatile/JLabLQCD/eromero/promises
