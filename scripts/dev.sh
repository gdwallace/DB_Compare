#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements-dev.txt

if [[ ! -d web/node_modules ]]; then
  (cd web && npm install)
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
trap 'kill "$API_PID"' EXIT
cd web
npm run dev
