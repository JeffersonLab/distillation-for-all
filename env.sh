#
# Environ variables used by various scripts.
#
# PLEASE set these up before calling any of the scripts here!

# JLab access to /mss, /cache, and node to run srmPendingRequest
export JLAB_REMOTE="ssh -J login.jlab.org qcdi1402"
# The id of this facility
export THIS_FACILITY="jz"
# Path in the facility to store configuration, eigenvectors, ...
export LOCAL_CACHE=/scratch/whatever
# Path in the facility to store SLURM scripts, XML, and output
export LOCAL_RUN=$PWD/runs
# Path to remote promises
export REMOTE_PROMISES=$PWD/runs
