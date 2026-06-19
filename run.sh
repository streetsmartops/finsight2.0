#!/bin/bash
# FinSight — launch the executive cockpit
set -e
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
echo "FinSight cockpit -> http://localhost:8000"
echo "(LLM mode: ${ANTHROPIC_API_KEY:+enabled}${ANTHROPIC_API_KEY:-template fallback})"
uvicorn api.main:app --reload --port 8000
