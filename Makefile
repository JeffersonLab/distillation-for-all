JSON_FILES := ensembles.json facilities.json streams.json artifacts.json summary.json
PYTHON_FILES := kaon.py create_chroma_job.py
BASH_FILES := kaon-create-jobs-eigs.sh kaon-get-files-transitioning-to-cache.sh kaon-get-from-tape-remote.sh kaon-get-promises.sh kaon-get-slurm-status.sh kaon-launch-jobs.sh kaon-promise.sh kaon-remote-cp.sh kaon-rm-promise.sh

format:
	for i in ${JSON_FILES}; do echo Formatting $$i && python -m json.tool $$i $$i.new && mv $$i.new $$i ; done
	for i in ${PYTHON_FILES} ; do echo Fromatting $$i && autopep8 -v -i --max-line-length 100 $$i ; done
	for i in ${BASH_FILES} ; do echo Fromatting $$i && sed -i 's/\t/    /' $$i ; done

test:
	./kaon.py --test
