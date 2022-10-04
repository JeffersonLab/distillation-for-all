#!/bin/bash

. env.sh

# Constrain the goals for ensembles active in this facility
./kaon.py facilities.json --facility $THIS_FACILITY --output-format schema > goals-facility.json

# Check the capabilities of this facility
do_eigs="`./kaon.py facilities.json --facility $THIS_FACILITY --show do_eigs`"
max_promises="`./kaon.py facilities.json --facility $THIS_FACILITY --show max_promises`"
max_eig_promises="0"
[ $do_eigs == yes ] && max_eig_promises="${max_promises}"

#
# Compute the missing eigenvectors
#

# Set scope, work with configurations and eigenvector from a stream and a range of trajectories
scope="facilities.json ensembles_32_64.json artifacts.json goals-facility.json"

# Iteratively run the following steps until the number of configuration without an eigenvector is zero
while true ; do
	# a) Capture all information about the goals
	./kaon.py $scope --output-format schema --log > scope.json
	exit 0

	# b) Copy back configurations and eigenvectors that are not at jlab's tape
	./kaon.py scope.json --cfg_file_remote_status promised none --cfg_file_status "local" --show cfg_file | kaon-remote-cp.sh here jlab
	./kaon.py scope.json --eig_file_remote_status promised none --eig_file_status "local" --show eig_file | kaon-remote-cp.sh here jlab

	# b) Remove promises for local eigenvectors that are at jlab
	./kaon.py scope.json --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status "local" --show eig_file | kaon-rm-promise.sh

	# c) Promise up to some number of eigenvectors to compute
	num_promises="`./kaon.py scope.json --eig_file_promiser $THIS_FACILITY --show eig_file | wc -l`"
	if [ $num_promises -lt $max_eig_promises ]; then
		./kaon.py scope.json --eig_file_remote_status none --eig_file_status none --show eig_file | head -$(( max_eig_promises - num_promises )) | kaon-promise.sh
	fi

	# d) Bring to cache configurations that doesn't have an eigenvector file associated and are on tape
	./kaon.py scope.json --cfg_file_remote_status tape --cfg_file_status none --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file | kaon-get-from-tape-remote.sh
	
	# e) Bring to this facility configurations that doesn't have an eigenvector file associated and are on cache at jlab
	./kaon.py scope.json --cfg_file_remote_status cache --cfg_file_status none --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file | kaon-remote-cp.sh jlab here
	
	# f) Create eigenvectors from configurations that are local and doesn't have an eigenvector file associated
	./kaon.py scope.json --cfg_file_status "local" --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file smear_fact smear_num default_vecs eig_default_file --output-format schema | launch-eigs.sh

	# Wait a bit, pal, things move slowly and we don't need to react at every second
	sleep $(( 30 * 60 ))
done
