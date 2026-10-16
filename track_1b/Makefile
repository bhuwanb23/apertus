.PHONY: run build verify-local

# Judges run this from track_1b/ on a clean checkout (Docker).
run:
	docker compose run --rm --build app

build:
	docker compose build

# Without Docker (dev): same verification against fixtures.
verify-local:
	python src/run.py
