#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8000}"

for i in {1..30}; do
  curl -fsS "$BASE/" >/dev/null || true
  curl -fsS "$BASE/health" >/dev/null || true
  curl -fsS "$BASE/reports" >/dev/null || true
  curl -fsS "$BASE/debug/trace" >/dev/null || true
  sleep 0.2
done

