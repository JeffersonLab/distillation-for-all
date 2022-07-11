format:
	python -m json.tool ensembles.json ensembles.json.new && mv ensembles.json.new ensembles.json
	autopep8 -v -i --max-line-length 100 kaon.py
