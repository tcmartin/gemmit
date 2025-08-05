#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="1.0.0"
TAG="v$VERSION"

echo -e "${BLUE}🚀 Creating GitHub Release for $TAG${NC}"
echo "============================================"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Install it with: brew install gh"
    echo "Then authenticate with: gh auth login"
    exit 1
fi

# Check if we're authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

# Check if artifacts exist
DIST_DIR="$ROOT/desktop/dist"
if [[ ! -d "$DIST_DIR" ]]; then
    echo -e "${RED}❌ Build artifacts not found. Run the build first:${NC}"
    echo "cd desktop && npm run build:all"
    exit 1
fi

echo -e "${YELLOW}📋 Found release artifacts:${NC}"
ls -la "$DIST_DIR"/*.{dmg,exe,AppImage,deb} 2>/dev/null || echo "No release artifacts found"

# Create release notes
RELEASE_NOTES="# Gemmit v$VERSION

## 🚀 Features
- Cross-platform desktop application (macOS, Windows, Linux)
- AI-powered development assistant with Gemini integration
- Real-time streaming chat interface
- Project management in ~/Gemmit_Projects
- Built-in file operations and project scaffolding
- PocketFlow methodology integration

## 📦 Downloads
- **macOS**: Download the .dmg file for your architecture (Intel or Apple Silicon)
- **Windows**: Download the Setup .exe file (supports both x64 and x86)
- **Linux**: Download the .AppImage for universal compatibility or .deb for Debian/Ubuntu

## 🔧 Installation
1. Download the appropriate file for your platform
2. Install/run the application
3. The app will automatically set up your workspace in ~/Gemmit_Projects

## 🐛 Known Issues
- macOS builds are not code-signed (you may need to allow in Security & Privacy settings)
- First launch may take a moment to initialize the AI backend

## 🤝 Support
If you encounter any issues, please report them on our [GitHub Issues](https://github.com/tcmartin/gemmit/issues) page.

---
Built with ❤️ using Electron and Python"

# Create the release
echo -e "${YELLOW}🏷️  Creating GitHub release...${NC}"
gh release create "$TAG" \
    --title "Gemmit v$VERSION" \
    --notes "$RELEASE_NOTES" \
    --draft \
    "$DIST_DIR/gemmit-1.0.0.dmg" \
    "$DIST_DIR/gemmit-1.0.0-arm64.dmg" \
    "$DIST_DIR/gemmit Setup 1.0.0.exe" \
    "$DIST_DIR/gemmit-1.0.0.AppImage" \
    "$DIST_DIR/desktop_1.0.0_amd64.deb"

echo -e "${GREEN}✅ GitHub release created successfully!${NC}"
echo -e "${BLUE}🌐 View at: https://github.com/tcmartin/gemmit/releases/tag/$TAG${NC}"
echo -e "${YELLOW}📝 The release is created as a draft. Edit and publish it when ready.${NC}"