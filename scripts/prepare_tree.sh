#!/usr/bin/env bash
set -euo pipefail
mkdir -p app server
mv *.html app/
mv backend.py server/
cat > server/requirements.txt <<'EOF'
websockets>=12.0
aiohttp>=3.9
EOF
echo "Tree prepared."

