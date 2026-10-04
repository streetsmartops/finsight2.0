#!/usr/bin/env bash
# FinSight — one-command live demo
#
#   ./demo/demo.sh            # install deps, run tests, start cockpit, smoke-test, open browser
#   ./demo/demo.sh --offline  # force template mode even if ANTHROPIC_API_KEY is set
#   ./demo/demo.sh --docker   # same, but run inside docker compose
#   ./demo/demo.sh --stop     # stop a background demo server
#
# Env: PORT (default 8000), SKIP_INSTALL=1, SKIP_TESTS=1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"
PID_FILE="$ROOT/.demo-server.pid"
LOG_FILE="$ROOT/.demo-server.log"
MODE="local"

for arg in "$@"; do
  case "$arg" in
    --offline) unset ANTHROPIC_API_KEY ;;
    --docker)  MODE="docker" ;;
    --stop)    MODE="stop" ;;
    -h|--help) sed -n 2,10p "$0"; exit 0 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1;32m▶ %s\033[0m\n' "$*"; }

open_browser() {
  if command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null; then open "$URL" || true
  fi
}

if [[ "$MODE" == "stop" ]]; then
  if [[ -f "$PID_FILE" ]]; then kill "$(cat "$PID_FILE")" 2>/dev/null || true; rm -f "$PID_FILE"; fi
  docker compose down 2>/dev/null || true
  say "demo stopped"; exit 0
fi

if [[ "$MODE" == "docker" ]]; then
  say "Building + starting container on $URL"
  FINSIGHT_PORT="$PORT" docker compose up --build -d
  "$ROOT/demo/smoke_test.sh" "$URL"
  open_browser
  say "Cockpit live at $URL   (stop: ./demo/demo.sh --stop)"
  exit 0
fi

PY="${PYTHON:-python3}"
if [[ -z "${SKIP_INSTALL:-}" ]]; then
  if [[ ! -d .venv ]]; then say "Creating .venv"; "$PY" -m venv .venv; fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  say "Installing dependencies"
  pip install -q --upgrade pip
  pip install -q numpy pandas scikit-learn fastapi "uvicorn[standard]" pydantic anthropic pytest
elif [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ -z "${SKIP_TESTS:-}" ]]; then
  say "Running test suite (engines + grounding contract)"
  python -m pytest tests -q
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  say "Stopping previous demo server"; kill "$(cat "$PID_FILE")" || true; sleep 1
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  say "LLM mode: Claude composes answers (falls back to template on any error)"
else
  say "LLM mode: deterministic template (offline-safe)"
fi

say "Starting cockpit on $URL"
nohup python -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT" >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

"$ROOT/demo/smoke_test.sh" "$URL"
open_browser
say "Cockpit live at $URL   (logs: $LOG_FILE · stop: ./demo/demo.sh --stop)"
say "Presenter guide: demo/PRESENTER_GUIDE.md"
