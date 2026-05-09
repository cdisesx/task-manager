#!/usr/bin/env bash
set -euo pipefail
export PYTHONUTF8=1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$SCRIPT_DIR/config/config.json" ]; then
  echo "[ERR] config/config.json not found."
  echo "Please copy config/config.example.json to config/config.json and fill in your values."
  exit 1
fi
python -m pip install -r "$SCRIPT_DIR/requirements.txt"
cd "$SCRIPT_DIR/dashboard"
if [ ! -d "node_modules" ]; then
  echo "     Installing..."
  npm install
fi
DASHBOARD_PORT=$(cd "$SCRIPT_DIR" && node -e "const c=JSON.parse(require('fs').readFileSync('config/config.json','utf8'));console.log(c.dashboard.port||3010)")
echo "Dashboard will be available at http://localhost:$DASHBOARD_PORT"
node server.js
