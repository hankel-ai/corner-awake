#!/bin/bash
# ============================================================
#  Corner Awake - macOS installer + launcher
#  Run once:  bash install_and_run.sh
#  Creates a private .venv next to this script (avoids the
#  "externally-managed-environment" pip error on Homebrew
#  Python), installs pystray + Pillow, then launches the app.
#  After that, use:  bash run.sh
# ============================================================
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
fi

if [ ! -x "$DIR/.venv/bin/python" ]; then
    echo "Creating virtual environment in $DIR/.venv ..."
    python3 -m venv "$DIR/.venv"
fi

echo "Installing pystray and Pillow (pystray pulls in pyobjc on macOS) ..."
"$DIR/.venv/bin/python" -m pip install --upgrade --quiet pip
"$DIR/.venv/bin/python" -m pip install --upgrade --quiet pystray Pillow

echo "Dependencies installed."
bash "$DIR/run.sh"

echo ""
echo "Usage:"
echo "  - Hold mouse in LOWER-RIGHT corner -- sleep blocked  (rising beep + green icon)"
echo "  - Move mouse away                  -- sleep allowed  (falling beep + grey icon)"
echo "  - Click the menu bar icon -- Settings / Quit"
echo ""
echo "If a macOS hot corner is set on the lower-right, it fires too when you hold the mouse there."
echo "Remove it, or give it a modifier key: System Settings > Desktop & Dock > Hot Corners."
