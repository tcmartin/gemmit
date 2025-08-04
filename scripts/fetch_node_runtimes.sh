#!/usr/bin/env bash
#
# fetch_node_runtimes.sh
# ──────────────────────
# Download the latest Node 20-LTS runtime for each desktop arch,
# copy just  ▸ bin/node (node.exe on Win)  and  ▸ npm/  into
# desktop/resources/bin/<platform>/ .
#
# Platforms handled:
#   darwin-arm64  → mac-arm64
#   darwin-x64    → mac-x64
#   linux-x64     → linux
#   win-x64       → win
#
# Requires: curl, tar, unzip, jq.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BINROOT="$ROOT/desktop/resources/bin"
mkdir -p "$BINROOT"

# ───────────────────────────────────────────────────────────────
# 1. Work out the latest v20.x.y
# ───────────────────────────────────────────────────────────────
echo "🔎 Fetching Node release index…"
LATEST=$(curl -sSL https://nodejs.org/dist/index.json |
         jq -r '[ .[]
                   | select(.version | startswith("v20."))      # keep 20.x
                   | select(.lts != false)                      # only LTS
                 ][0].version')

if [[ -z "$LATEST" ]]; then
  echo "❌ Could not determine latest Node 20 release." >&2
  exit 1
fi

echo "✨ Latest 20-LTS detected:  $LATEST"
BASE_URL="https://nodejs.org/dist/$LATEST"

# ───────────────────────────────────────────────────────────────
# 2. Helper: download iff checksum mismatch / missing
# ───────────────────────────────────────────────────────────────
download_if_needed () {
  local url="$1" file="$2" sha="$3"
  if [[ -f "$file" ]]; then
    local have
    have=$(shasum -a 256 "$file" | awk '{print $1}')
    if [[ "$have" == "$sha" ]]; then
      echo "✓ $file already verified"
      return
    fi
    echo "↻ checksum mismatch – redownloading $file"
    rm -f "$file"
  fi
  echo "↓ $file"
  curl -#L "$url" -o "$file"
  echo "$sha  $file" | shasum -a 256 -c -
}

# ───────────────────────────────────────────────────────────────
# 3. Platform matrix
# ───────────────────────────────────────────────────────────────
PLATFORMS=(
  "darwin-arm64 mac-arm64 tar.gz"
  "darwin-x64   mac-x64  tar.gz"
  "linux-x64    linux    tar.xz"
  "win-x64      win      zip"
)

WORK=/tmp/vibe-node-fetch
rm -rf "$WORK" && mkdir -p "$WORK"
pushd "$WORK" >/dev/null

# Grab SHASUMS file once
curl -sSL "$BASE_URL/SHASUMS256.txt" -o SHASUMS256.txt

for entry in "${PLATFORMS[@]}"; do
  set -- $entry
  SUFFIX=$1 DEST=$2 EXT=$3

  ARCHIVE="node-${LATEST}-${SUFFIX}.${EXT}"
  SHA=$(grep " $ARCHIVE\$" SHASUMS256.txt | awk '{print $1}')
  download_if_needed "$BASE_URL/$ARCHIVE" "$ARCHIVE" "$SHA"

  echo "▸ extracting $ARCHIVE → $DEST"
  rm -rf "node-${LATEST}-${SUFFIX}"
  case $EXT in
    tar.gz) tar -xzf "$ARCHIVE"   ;;
    tar.xz) tar -xJf "$ARCHIVE"   ;;
    zip)    unzip -q "$ARCHIVE"   ;;
  esac

  SRC_DIR="node-${LATEST}-${SUFFIX}"
  DEST_DIR="$BINROOT/$DEST"
  rm -rf "$DEST_DIR" && mkdir -p "$DEST_DIR"

  # node binary
  if [[ "$DEST" == "win" ]]; then
    cp "$SRC_DIR/node.exe" "$DEST_DIR/"
  else
    cp "$SRC_DIR/bin/node" "$DEST_DIR/"
  fi

  # npm (copy entire folder)
  mkdir -p "$DEST_DIR/npm"
  # npm (copy entire folder)
  mkdir -p "$DEST_DIR/npm"
  if [[ -d "$SRC_DIR/lib/node_modules/npm" ]]; then         # mac / linux
    cp -R "$SRC_DIR/lib/node_modules/npm" "$DEST_DIR/npm/"
  else                                                      # windows layout
    cp -R "$SRC_DIR/node_modules/npm"      "$DEST_DIR/npm/"
  fi

  echo "✓ runtime staged in $DEST_DIR"
done

popd >/dev/null
echo "🎉 All runtimes ready under desktop/resources/bin/"

