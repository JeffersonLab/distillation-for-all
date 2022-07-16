JSON_FILES := ensembles.json facilities.json streams.json artifacts.json summary.json
PYTHON_FILES := kaon.py create_chroma_job.py
BASH_FILES := kaon-create-jobs-eigs.sh kaon-get-files-transitioning-to-cache.sh kaon-get-from-tape-remote.sh kaon-get-promises.sh kaon-get-slurm-status.sh kaon-launch-jobs.sh kaon-promise.sh kaon-remote-cp.sh kaon-rm-promise.sh
PYTHON ?= python
SHELL := bash

format: check_python_version
	for i in ${JSON_FILES}; do echo Formatting $$i && ${PYTHON} -m json.tool $$i $$i.new && mv $$i.new $$i ; done
	for i in ${PYTHON_FILES} ; do echo Fromatting $$i && autopep8 -v -i --max-line-length 100 $$i ; done
	for i in ${BASH_FILES} ; do echo Fromatting $$i && sed -i 's/\t/    /' $$i ; done

test: check_python_version
	./kaon.py --test

check_python_version:
	echo $$'import sys\nif sys.version_info[0] < 3: raise Exception("Please use python 3")' | ${PYTHON} 
