format:
	for i in ensembles.json facilities.json ; do echo Formatting $$i && python -m json.tool $$i $$i.new && mv $$i.new $$i ; done
	for i in kaon.py create_chroma_job.py ; do echo Fromatting $$i && autopep8 -v -i --max-line-length 100 $$i ; done
