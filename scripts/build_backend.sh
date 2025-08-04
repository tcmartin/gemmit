#!/usr/bin/env bash
set -euo pipefail
PY=python3          # adjust if multiple versions
$PY -m pip install --upgrade pip pyinstaller -r server/requirements.txt

cd server
pyinstaller backend.py \
    --onefile --name backend \
    --add-data "../app:app"
mv dist/backend* ../desktop/resources/bin/$(./scripts/os_folder.sh)/

