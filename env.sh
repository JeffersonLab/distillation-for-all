#
# Environ variables used by various scripts.
#
# PLEASE set these up before calling any of the scripts here!

# JLab tape directory access
JLAB_REMOTE_MSS="ssh -J login.jlab.org qcdi1402"
# JLab cache directory access
JLAB_REMOTE_CACHE="ssh -J login.jlab.org qcdi1402"
export THIS_FACILITY="jz"
# Path in the facility to store configuration, eigenvectors, ...
export LOCAL_CACHE=/scratch/whatever
# Path in the facility to store SLURM scripts, XML, and output
export LOCAL_RUN=$PWD/runs
# Path to remote promises
export REMOTE_PROMISES=$PWD/runs
# Maximum number of files promised to be computed in this facility at a time


