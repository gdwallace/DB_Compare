#!/usr/bin/env bash
# Set up the project (venv, Python/Node deps, .env) and start the API + UI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing Python packages..."
python -m pip install -q -U pip
python -m pip install -q -r requirements-dev.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill APPIAN_PASSWORD and APPIAN_STAGE_PASSWORD before comparing live servers."
fi

echo "Installing web packages..."
(cd web && npm install)

echo "Starting API on http://127.0.0.1:8000 and UI on http://127.0.0.1:5173"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
cd web
npm run dev
