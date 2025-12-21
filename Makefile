.PHONY: lint test notify-digest-flush

lint:
	python3 -m ruff check .

test:
	python3 -m pytest -q

notify-digest-flush:
	python3 scripts/flush_digest.py

