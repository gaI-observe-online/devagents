.PHONY: test-env-up test-env-down test-smoke test

test-env-up:
	docker compose -f compose.test.yml up -d --build

test-env-down:
	docker compose -f compose.test.yml down -v

test-smoke:
	bash scripts/smoke_traffic.sh http://localhost:8000

test:
	python -m pytest -q

