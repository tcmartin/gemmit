#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=python3                     # use your interpreter if different

# ── 1. Create virtual environment and install deps ─────────────
VENV_DIR="$ROOT/server/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PY -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
pip install --upgrade pip
pip install -r "$ROOT/server/requirements.txt" pyinstaller

# ── 2. Build one-file binary with static web assets ─────────────
cd "$ROOT/server"
pyinstaller backend.py \
  --onefile --name backend \
  --add-data "$ROOT/app:app"

# ── 3. Move artefact next to Electron resources ─────────────────
cd "$ROOT"
OS_FOLDER="$("$ROOT/scripts/os_folder.sh")"
BIN_DIR="$ROOT/desktop/resources/bin/$OS_FOLDER"
mkdir -p "$BIN_DIR"

# backend (mac/linux) or backend.exe (win) → same folder
mv server/dist/backend* "$BIN_DIR/"

echo "✅ Backend binary placed in $BIN_DIR"

