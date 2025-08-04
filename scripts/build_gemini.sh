#!/usr/bin/env bash
set -euo pipefail
npm i -g pkg
TARGETS=("node18-win-x64" "node18-macos-x64" "node18-macos-arm64" "node18-linux-x64")
for T in "${TARGETS[@]}"; do
  DIR=${T#node18-}; DIR=${DIR/-/\/}   # win/x64 → win/x64
  OUT=desktop/resources/bin/$DIR
  mkdir -p "$OUT"
  pkg $(npm root -g)/@google/gemini-cli/dist/index.js \
      --targets "$T" --output "$OUT/gemini-cli"
done

