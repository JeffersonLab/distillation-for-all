JSON_FILES := ensembles.json facilities.json streams.json artifacts.json summary.json
PYTHON_FILES := kaon.py create_chroma_job.py

format:
	for i in ${JSON_FILES}; do echo Formatting $$i && python -m json.tool $$i $$i.new && mv $$i.new $$i ; done
	for i in ${PYTHON_FILES} ; do echo Fromatting $$i && autopep8 -v -i --max-line-length 100 $$i ; done

test:
	./kaon.py --test
