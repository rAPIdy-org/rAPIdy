#!/usr/bin/env bash
set -euo pipefail

TAG="${RELEASE_TAG:?RELEASE_TAG required}"

if [[ "$TAG" =~ ^(rapidy|rapidy-core|rapidy-client)-v([0-9]+\.[0-9]+\.[0-9]+.*)$ ]]; then
    DIST="${BASH_REMATCH[1]}"
    VERSION="${BASH_REMATCH[2]}"
else
    echo "unrecognized release tag: $TAG" >&2
    exit 1
fi

case "$DIST" in
    rapidy)
        PACKAGE_DIR="packages/rapidy"
        ;;
    rapidy-core)
        PACKAGE_DIR="packages/rapidy_core"
        ;;
    rapidy-client)
        PACKAGE_DIR="packages/rapidy_client"
        ;;
esac

if [[ "${1:-}" == "--check-version" ]]; then
    PACKAGE_VERSION="$(sed -nE 's/^version = "([^"]+)"/\1/p' "$PACKAGE_DIR/pyproject.toml" | head -n 1)"
    if [[ "$VERSION" != "$PACKAGE_VERSION" ]]; then
        echo "tag $VERSION != [project].version $PACKAGE_VERSION ($PACKAGE_DIR)" >&2
        exit 1
    fi
fi

echo "$DIST"
