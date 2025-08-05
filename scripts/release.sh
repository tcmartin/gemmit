#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}🚀 Gemmit Release Process${NC}"
echo "=========================="

# Check if version is provided
if [[ $# -eq 0 ]]; then
    echo -e "${RED}❌ Please provide a version number${NC}"
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.1"
    exit 1
fi

VERSION=$1
TAG="v$VERSION"

# Validate version format (basic semver check)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid version format. Use semantic versioning (e.g., 1.0.1)${NC}"
    exit 1
fi

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo -e "${RED}❌ Tag $TAG already exists${NC}"
    exit 1
fi

echo -e "${BLUE}Preparing release $TAG${NC}"

# Run the preparation script
echo -e "${YELLOW}🔧 Running release preparation...${NC}"
./scripts/prepare_release.sh

# Update version in package.json
echo -e "${YELLOW}📝 Updating version to $VERSION...${NC}"
cd "$ROOT/desktop"
npm version "$VERSION" --no-git-tag-version

# Commit version change
cd "$ROOT"
git add desktop/package.json
git commit -m "chore: bump version to $VERSION"

# Create and push tag
echo -e "${YELLOW}🏷️  Creating and pushing tag $TAG...${NC}"
git tag -a "$TAG" -m "Release $TAG"
git push origin main
git push origin "$TAG"

echo -e "${GREEN}✅ Release $TAG created and pushed!${NC}"
echo -e "${BLUE}GitHub Actions will now build and create the release automatically.${NC}"
echo -e "${BLUE}Check: https://github.com/tcmartin/gemmit/actions${NC}"