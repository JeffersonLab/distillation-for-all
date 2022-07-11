#!/bin/bash

# JLab endpoing
export THIS_FACILITY="jz"
# Path in the facility to store configuration, eigenvectors, ...
export LOCAL_CACHE=/scratch/whatever
# Path in the facility to store SLURM scripts, XML, and output
export LOCAL_RUN=$PWD/runs
# Path to remote promises
export REMOTE_PROMISES=$PWD/runs
# Maximum number of files promised to be computed in this facility at a time

cat > streams.json << EOF
[
	{
        	"values": [
			{"kind": "stream", "cfg_dir": "cl21_48_96_b6p3_m0p2416_m0p2050-rightColorvecs", "cfg_name": "cl21_48_96_b6p3_m0p2416_m0p2050"},
			{"kind": "stream", "cfg_dir": "cl21_48_96_b6p3_m0p2416_m0p2050-1000-rightColorvecs", "cfg_name": "cl21_48_96_b6p3_m0p2416_m0p2050"},
			{"kind": "stream", "cfg_dir": "cl21_48_96_b6p3_m0p2416_m0p2050-djm-streams-rightColorvecs/cl21_48_96_b6p3_m0p2416_m0p2050", "cfg_name": "cl21_48_96_b6p3_m0p2416_m0p2050"}
         	],
		"id": "stream-{cfg_dir}"
	}
]
EOF
cat > artifacts.json << EOF
[
	{
		"name":"mss",
		"depends": { "kind": ["stream"] },
                "executor":{
			"command": "ssh -J login.jlab.org qcdi1402 find /mss/lattice/isoClover/{cfg_dir}",
                	"return-attributes": ["file"]
		},
                "update":{"kind":"file", "status":"tape", "remote_status": "remote"},
		"id": "file-{file}"
        }, {
                "name":"cache",
		"depends": { "kind": ["stream"] },
                "executor": {
			"command": "ssh -J login.jlab.org qcdi1402 find /cache/isoClover/{cfg_dir} | while read file ; do echo \${{file#/cache/isoClover/}}; done",
                	"return-attributes": "file"
		},
                "update":{"kind": "file", "remove_status":"cached"},
		"id": "file-{file}"
        }, {
                "name":"fix status for files being brought from tape",
		"description": "avoid operating with files not fully copied from tape",
                "executor": {
			"command": "kaon-get-files-transitioning-to-cache.sh",
                	"return-attributes": "file"
		},
                "update":{"kind": "file", "remote_status":"none"},
		"id": "file-{file}"
        }, {
                "name":"remote promises",
		"depends": { "kind": ["stream"] },
                "executor": {
			"command": "kaon-get-promises.sh {cfg_dir}",
                	"return-attributes": ["file", "promiser"]
		},
                "update":{"kind": "file", "remote_status":"promised"},
		"id": "file-{file}"
        }, {
                "name":"local cache",
		"depends": { "kind": ["stream"] },
                "defaults":{"remote_status": "none"},
                "executor": {
			"command": "find ${LOCAL_CACHE}/{cfg_dir} \\! -name '*.globus-to-*' | while read file ; do echo \${{file#${LOCAL_CACHE}/}}; done",
                	"return-attributes": ["file"]
		},
                "update":{"kind": "file", "status":"local" },
		"id": "file-{file}"
        }, {
                "name":"track files being copied from other facilities to this one",
		"depends": { "kind": ["stream"] },
                "executor": {
			"command": "find ${LOCAL_CACHE}/{cfg_dir} -name '*.globus-to-here' | while read file ; do a=\\"\${{file#${LOCAL_CACHE}/}}\\"; echo \${{a%.globus-to-here}}; done",
                	"return-attributes": ["file"]
		},
                "update":{"kind": "file", "status":"promised" },
		"id": "file-{file}"
        }, {
                "name":"track files being copied to other facilities from this one",
		"depends": { "kind": ["stream"] },
                "executor": {
			"command": "find ${LOCAL_CACHE}/{cfg_dir} -name '*.globus-to-jlab' | while read file ; do a=\\"\${{file#${LOCAL_CACHE}/}}\\"; echo \${{a%.globus-to-jlab}}; done",
                	"return-attributes": ["file"]
		},
                "update":{"kind": "file", "remote_status":"promised" },
		"id": "file-{file}"
        }, {
                "name":"local jobs",
		"depends": { "kind": ["stream"] },
                "defaults":{"remote_status": "none"},
                "executor": {
			"command": "kaon-get-slurm-status.sh ${LOCAL_RUNS}/{cfg_dir}",
                	"return_attributes": ["file", "status"]
		},
                "update":{"kind": "file"},
		"id": "file-{file}"
        }, {
		"depends": {
			"kind": ["file"],
			"file": {
				"matching-re": "{cfg_dir}/cfgs/{cfg_prefix}_cfg_(?P<cfg_num>\\\\d+).lime$",
				"copy-as": "file_cfg"
			},
			"status": { "copy-as": "cfg_file_status" },
			"remote_status": { "copy-as": "cfg_file_remote_status" }
		},
		"update": {"kind":"configuration"},
        	"id": "cfg-{cfg_dir}-{cfg_num}"
	}, {
		"name": "already computed eigenvectors",
		"depends": {
			"kind": ["file"],
			"file": {
				"matching-re": "{cfg_dir}/eigs_mod/{cfg_prefix}\\\\.3d\\\\.eigs\\\\.n(?P<eig_num_vecs>\\\\d+).mod(?P<cfg_num>\\\\d+)$",
				"copy-as": "eig_file"
			},
			"status": { "copy-as": "eig_file_status" },
			"remote_status": { "copy-as": "eig_file_remote_status" }
		},
		"update": {"kind":"eigenvector"},
        	"id": "eig-{cfg_dir}-{cfg_num}"
	}, {
		"name": "potential eigenvector from a configuration"
		"depends": {
			"kind": ["configuration"],
			"eig_default_file": {
				"interpolate": "{cfg_dir}/eigs_mod/{cfg_prefix}.3d.eigs.n{default_num_vecs}.mod{cfg_num}",
			},
			"eig_id": {
				"interpolate": "${LOCAL_RUN}/{cfg_dir}/eigs_mod/eigs.cnf{cfg_num}.n{default_num_vecs}.sf{smear_fact}.sn{smear_num}",
			}
		},
		"defaults": { "eig_file": "none", "eig_file_status": "none", "eig_file_remote_status":"none"},
		"update": {"kind":"eigenvector"},
        	"id": "eig-{cfg_dir}-{cfg_num}"
	}, {
		"depends": {
			"kind": ["file"],
			"file": {
				"matching-glob": "{cfg_dir}/prop_db/{cfg_prefix}.prop.n{prop_num_vecs}.light.t0_{prop_t_source}.sdb{cfg_num}",
				"copy-as": "file_prop"
			},
			"status": { "copy-as": "prop_file_status" },
			"remote_status": { "copy-as": "prop_file_remote_status" }
		},
		"update": {"kind":"propagator", "prop_phase":"0.00"},
		"id": "prop-{cfg_name}-{cfg_num}-{prop_phase}-{prop_t_source}"
	}, {
		"depends": {
			"kind": ["file"],
			"file": {
				"matching-glob": "{cfg_dir}/phase/prop_db/{cfg_prefix}.prop.n{prop_num_vecs}.light.t0_{prop_t_source}.phased_{prop_phase}.sdb{cfg_num}",
				"copy-as": "file_prop"
			},
			"status": { "copy-as": "prop_file_status" },
			"remote_status": { "copy-as": "prop_file_remote_status" }
		},
		"update": {"kind":"propagator" },
		"id": "prop-{cfg_name}-{cfg_num}-{prop_phase}-{prop_t_source}"
	}, {
		"depends": {
			"kind": ["file"],
			"file": {
				"matching-re": "{cfg_dir}/unsmeared_meson_dbs.*/unsmeared_meson\\.phased_d001_(?P<gprop_phase>\\d+)\\.n(?P<gprop_num_vecs>\\d+)\\.(?P<gprop_t_source>\\d+)\\.tsnk_(?P<gprop_t_seps>\\w+)\\.Gamma_.*\\.sdb(?P<cfg_num>\\d+)(>P<gprop_suffix>.*)$",
				},
				"copy-as": "file_gprop"
			}
		},
		"update": {"kind":"genprop" },
		"id": "genprop-{cfg_name}-{cfg_num}-{gprop_phase}-{gprop_t_source}-{gprop_t_seps}"
	}
]
EOF

#
# Compute the missing eigenvectors
#

# Set scope, work with configurations and eigenvector from a stream and a range of trajectories
scope="ensemble.json artifacts.json --cfg_dir cl21_48_96_b6p3_m0p2416_m0p2050-rightColorvecs --cfg_num 1:1000 --kind configuration eigenvector"

# Iteratively run the following steps until the number of configuration without an eigenvector is zero
while true ; do
	cat goals.txt | while read scope ; do
		# a) Capture all information about the goals
		./kaon.py $scope --output-format schema > scope.json

		# b) Copy back configurations and eigenvectors that are not at jlab's tape
		./kaon.py scope.json --cfg_file_remote_status promised none --cfg_file_status "local" --show cfg_file | kaon-remote-cp.sh here jlab
		./kaon.py scope.json --eig_file_remote_status promised none --eig_file_status "local" --show eig_file | kaon-remote-cp.sh here jlab

		# b) Remove promises for local eigenvectors that are at jlab
		./kaon.py scope.json --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status "local" --show eig_file | kaon-rm-promise.sh

		# c) Promise up to some number of eigenvectors to compute
		num_promises="`./kaon.py scope.json --eig_file_promiser $THIS_FACILITY --show eig_file | wc -l`"
		if [ $num_promises -lt $max_promises ]; then
			./kaon.py scope.json --eig_file_remote_status none --eig_file_status none --show eig_file | head -$(( max_promises - num_promises )) | kaon-promise.sh
		fi

		# d) Bring to cache configurations that doesn't have an eigenvector file associated and are on tape
		./kaon.py scope.json --cfg_file_remote_status tape --cfg_file_status none --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file | kaon-get-from-tape-remote.sh
		
		# e) Bring to this facility configurations that doesn't have an eigenvector file associated and are on cache at jlab
		./kaon.py scope.json --cfg_file_remote_status cache --cfg_file_status none --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file | kaon-remote-cp.sh jlab here
		
		# f) Create eigenvectors from configurations that are local and doesn't have an eigenvector file associated
		./kaon.py scope.json --cfg_file_status "local" --eig_file_remote_status promised --eig_file_promiser $THIS_FACILITY --eig_file_status none --show cfg_file smear_fact smear_num default_vecs eig_default_file --output-format schema | launch-eigs.sh
	done	

	# Wait a bit, pal, things move slowly and we don't need to react at every second
	sleep $(( 30 * 60 ))
done
