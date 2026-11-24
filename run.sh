#!/bin/bash
# ============================================================
#  Corner Awake - macOS launcher (no install)
#  Use install_and_run.sh for first-time setup.
#  Starts detached, so closing Terminal does not stop the app.
# ============================================================
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$DIR/.venv/bin/python"

if [ ! -x "$PY" ]; then
    echo "[ERROR] $PY not found. Run: bash install_and_run.sh"
    exit 1
fi

nohup "$PY" "$DIR/corner_awake.pyw" >/dev/null 2>&1 &
echo "Corner Awake started (look for the grey circle in the menu bar)."
