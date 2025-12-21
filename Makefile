.PHONY: lint test notify-digest-flush test-env-up test-smoke test-env-down

lint:
	python3 -m ruff check .

test:
	python3 -m pytest -q

notify-digest-flush:
	python3 scripts/flush_digest.py

test-env-up:
	@command -v docker >/dev/null 2>&1 || { echo "BLOCKED: docker not installed"; exit 2; }
	@docker compose up -d

test-smoke:
	@echo "Smoke checks:"
	@echo "  - Grafana: http://localhost:3000/api/health"
	@echo "  - Service: http://localhost:8000/health"
	@curl -fsS http://localhost:3000/api/health || { echo "FAIL: Grafana not reachable (is docker compose up?)"; exit 7; }
	@curl -fsS http://localhost:8000/health || { echo "FAIL: Service not reachable (is uvicorn running?)"; exit 7; }

test-env-down:
	@command -v docker >/dev/null 2>&1 || { echo "BLOCKED: docker not installed"; exit 2; }
	@docker compose down

