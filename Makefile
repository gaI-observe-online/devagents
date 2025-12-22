.PHONY: venv install up down verify reset obs-up obs-down test-env-up test-env-down test-smoke test test-integration test-docker notify-digest-flush lint \
        beta-up beta-down beta-verify beta-reset

PYTHON := python3
VENV := .venv
PORT ?= 8000
HOST ?= 127.0.0.1
GADOS_RUNTIME_DIR ?= .gados-runtime
OTEL_SDK_DISABLED ?= 1

define venv_python
$(VENV)/bin/python
endef

define venv_pip
$(VENV)/bin/pip
endef

define compose_cmd
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo "docker compose"; \
elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; \
else echo ""; fi
endef

# --- Dev hygiene ---
lint:
	$(call venv_python) -m ruff check .

venv:
	$(PYTHON) -m venv $(VENV)
	$(call venv_python) -m pip install --upgrade pip

install: venv
	$(call venv_pip) install -r requirements.txt
	$(call venv_pip) install -e gados-control-plane

# --- Run control-plane ---
up: install
	@mkdir -p "$(GADOS_RUNTIME_DIR)"
	@echo "Starting control-plane on http://$(HOST):$(PORT) (OTEL_SDK_DISABLED=$(OTEL_SDK_DISABLED))"
	@OTEL_SDK_DISABLED="$(OTEL_SDK_DISABLED)" GADOS_RUNTIME_DIR="$(GADOS_RUNTIME_DIR)" \
	  "$(VENV)/bin/uvicorn" gados_control_plane.main:app --host "$(HOST)" --port "$(PORT)" \
	  >"$(GADOS_RUNTIME_DIR)/control-plane.log" 2>&1 & echo $$! >"$(GADOS_RUNTIME_DIR)/control-plane.pid"
	@$(MAKE) verify
	@echo "Logs: $(GADOS_RUNTIME_DIR)/control-plane.log"

down:
	@if [ -f "$(GADOS_RUNTIME_DIR)/control-plane.pid" ]; then \
	  PID="$$(cat "$(GADOS_RUNTIME_DIR)/control-plane.pid")"; \
	  echo "Stopping control-plane (pid=$$PID)"; \
	  kill "$$PID" >/dev/null 2>&1 || true; \
	  rm -f "$(GADOS_RUNTIME_DIR)/control-plane.pid"; \
	else \
	  echo "No pid file found at $(GADOS_RUNTIME_DIR)/control-plane.pid"; \
	fi

# Cross-platform health check (no curl)
verify:
	@$(PYTHON) - <<'PY'
import sys, time, urllib.request
host = "$(HOST)"
port = "$(PORT)"
url = f"http://{host}:{port}/health"
for _ in range(40):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            if r.status < 400:
                print("OK: /health")
                sys.exit(0)
    except Exception:
        time.sleep(0.5)
print("FAIL: control-plane did not become healthy. Check $(GADOS_RUNTIME_DIR)/control-plane.log")
sys.exit(1)
PY

reset:
	rm -rf "$(GADOS_RUNTIME_DIR)"

# --- Observability stack ---
obs-up:
	@CMD="$$( $(compose_cmd) )"; \
	if [ -z "$$CMD" ]; then echo "Docker compose not available"; exit 1; fi; \
	$$CMD -f docker-compose.yml up -d

obs-down:
	@CMD="$$( $(compose_cmd) )"; \
	if [ -z "$$CMD" ]; then echo "Docker compose not available"; exit 1; fi; \
	$$CMD -f docker-compose.yml down -v

# --- Test environment (LGTM etc) ---
test-env-up:
	@CMD="$$( $(compose_cmd) )"; \
	if [ -z "$$CMD" ]; then echo "Docker compose not available"; exit 1; fi; \
	$$CMD -f compose.test.yml up -d --build

test-env-down:
	@CMD="$$( $(compose_cmd) )"; \
	if [ -z "$$CMD" ]; then echo "Docker compose not available"; exit 1; fi; \
	$$CMD -f compose.test.yml down -v

# Cross-platform smoke (replaces bash scripts/smoke_traffic.sh)
test-smoke:
	@$(PYTHON) - <<'PY'
import sys, time, urllib.request
url="http://localhost:8000/health"
for _ in range(30):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            if r.status < 400:
                print("OK:", url)
                sys.exit(0)
    except Exception:
        time.sleep(0.5)
print("FAIL:", url)
sys.exit(7)
PY

test:
	$(call venv_python) -m pytest -q -m "not integration"

test-integration:
	GADOS_RUN_INTEGRATION_TESTS=1 $(call venv_python) -m pytest -q tests/integration

test-docker: test-env-up test-smoke test test-integration test-env-down

notify-digest-flush:
	$(call venv_python) scripts/flush_digest.py

# --- Beta aliases (from 7358f45) ---
beta-up: up
beta-down: down
beta-verify: verify
beta-reset: reset
