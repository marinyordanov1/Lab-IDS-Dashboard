.PHONY: setup test run init-db ingest-sample ingest-sample-incremental watch-sample

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

test:
	.venv/bin/pytest

run:
	.venv/bin/uvicorn app:app --reload

init-db:
	.venv/bin/python manage.py init-db

ingest-sample:
	.venv/bin/python manage.py ingest-sample

ingest-sample-incremental:
	.venv/bin/python manage.py ingest-file --path data/sample/suricata_eve.json --incremental

watch-sample:
	.venv/bin/python manage.py watch-file --path data/sample/suricata_eve.json --poll-interval 2

