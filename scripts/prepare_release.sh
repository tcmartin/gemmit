#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}🚀 Gemmit Release Preparation${NC}"
echo "=================================="

# Check if we're on main/master branch
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    echo -e "${YELLOW}⚠️  Warning: You're not on main/master branch (current: $BRANCH)${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ You have uncommitted changes. Please commit or stash them first.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(node -p "require('$ROOT/desktop/package.json').version")
echo -e "${BLUE}Current version: $CURRENT_VERSION${NC}"

# Ask for new version
echo -e "${YELLOW}Enter new version (or press Enter to keep current):${NC}"
read -r NEW_VERSION
if [[ -z "$NEW_VERSION" ]]; then
    NEW_VERSION=$CURRENT_VERSION
fi

echo -e "${BLUE}Building release for version: $NEW_VERSION${NC}"

# Update version in package.json if changed
if [[ "$NEW_VERSION" != "$CURRENT_VERSION" ]]; then
    echo -e "${YELLOW}📝 Updating version in package.json...${NC}"
    cd "$ROOT/desktop"
    npm version "$NEW_VERSION" --no-git-tag-version
fi

# Build backend binary
echo -e "${YELLOW}🔨 Building backend binary...${NC}"
cd "$ROOT"
./scripts/build_backend.sh

# Install/update desktop dependencies
echo -e "${YELLOW}📦 Installing desktop dependencies...${NC}"
cd "$ROOT/desktop"
npm install

# Build for all platforms
echo -e "${YELLOW}🏗️  Building for all platforms...${NC}"
npm run build:all

echo -e "${GREEN}✅ Release build complete!${NC}"
echo -e "${BLUE}Built files are in: $ROOT/desktop/dist/${NC}"

# List built files
echo -e "${YELLOW}📋 Built artifacts:${NC}"
ls -la "$ROOT/desktop/dist/" | grep -E '\.(dmg|exe|AppImage|deb)$' || echo "No release artifacts found"

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Test the built applications"
echo "2. Create a git tag: git tag v$NEW_VERSION"
echo "3. Push the tag: git push origin v$NEW_VERSION"
echo "4. Create a GitHub release with the built artifacts"
echo ""
echo -e "${GREEN}🎉 Ready for release!${NC}"