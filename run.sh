#!/usr/bin/env bash
# Startet OSW (Open Sonos Web).  Nutzung: ./run.sh [--demo] [--port 8080]
set -euo pipefail
cd "$(dirname "$0")"
PORT=8080
while [[ $# -gt 0 ]]; do
  case "$1" in
    --demo) export SONOS_DEMO=1 ;;
    --port) PORT="$2"; shift ;;
    *) echo "Unbekannte Option: $1" >&2; exit 1 ;;
  esac
  shift
done
if [[ ! -x .venv/bin/uvicorn ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
