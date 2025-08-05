#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Gemmit macOS Gatekeeper Fix${NC}"
echo "=================================="

# Check if app exists in Applications
APP_PATH="/Applications/gemmit.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo -e "${RED}❌ Gemmit.app not found in /Applications${NC}"
    echo "Please install the app first by dragging it to Applications folder"
    exit 1
fi

echo -e "${YELLOW}📋 Current app attributes:${NC}"
xattr -l "$APP_PATH" || echo "No extended attributes found"

echo ""
echo -e "${YELLOW}🔧 Removing quarantine attribute...${NC}"

# Remove quarantine attribute
if xattr -d com.apple.quarantine "$APP_PATH" 2>/dev/null; then
    echo -e "${GREEN}✅ Quarantine attribute removed${NC}"
else
    echo -e "${YELLOW}⚠️  No quarantine attribute found (this is normal)${NC}"
fi

# Remove all extended attributes as backup
echo -e "${YELLOW}🧹 Removing all extended attributes...${NC}"
if sudo xattr -cr "$APP_PATH" 2>/dev/null; then
    echo -e "${GREEN}✅ All extended attributes cleared${NC}"
else
    echo -e "${YELLOW}⚠️  Could not clear all attributes (may need admin password)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Gemmit should now open without Gatekeeper warnings!${NC}"
echo -e "${BLUE}💡 Try opening the app from Applications folder${NC}"

# Offer to open the app
echo ""
read -p "Would you like to open Gemmit now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 Opening Gemmit...${NC}"
    open "$APP_PATH"
fi