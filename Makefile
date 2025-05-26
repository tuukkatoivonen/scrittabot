all: install

run:
	bash -c 'source venv/bin/activate && python scrittabot.py'

install:
	python -m venv venv #--system-site-packages
	bash -c 'source venv/bin/activate && pip install -r requirements.txt'
