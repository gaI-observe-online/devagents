.PHONY: test-env-up test-env-down test-smoke test test-integration notify-digest-flush

test-env-up:
	docker compose -f compose.test.yml up -d --build

test-env-down:
	docker compose -f compose.test.yml down -v

test-smoke:
	bash scripts/smoke_traffic.sh http://localhost:8000

test:
	python -m pytest -q -m "not integration"

test-integration:
	GADOS_RUN_INTEGRATION_TESTS=1 python -m pytest -q tests/integration

notify-digest-flush:
	python scripts/flush_digest.py

