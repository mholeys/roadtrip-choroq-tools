#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
APP_NAME="Q's Factory"
BUNDLE_ID="com.giovencostrategics.Q-s-Factory"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT_DIR/Q's Factory/Q's Factory.xcodeproj"
SCHEME="Q's Factory"

DERIVED_DATA="${QFACTORY_DERIVED_DATA:-/tmp/qfactory-derived}"
BUILD_CONFIG="${QFACTORY_CONFIGURATION:-Release}"

BUILD_PRODUCTS_DIR="$DERIVED_DATA/Build/Products/$BUILD_CONFIG"
APP_BUNDLE="$BUILD_PRODUCTS_DIR/$APP_NAME.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/$APP_NAME"

DIST_DIR="$ROOT_DIR/dist"
EXPORT_APP="$DIST_DIR/$APP_NAME.app"
ZIP_PATH="$DIST_DIR/$APP_NAME-macOS.zip"

cd "$ROOT_DIR"

pkill -x "$APP_NAME" >/dev/null 2>&1 || true

build_app() {
  xcodebuild \
    -project "$PROJECT" \
    -scheme "$SCHEME" \
    -configuration "$BUILD_CONFIG" \
    -derivedDataPath "$DERIVED_DATA" \
    build
}

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

export_app() {
  rm -rf "$DIST_DIR"
  mkdir -p "$DIST_DIR"

  # Copy the built .app bundle into dist
  cp -R "$APP_BUNDLE" "$EXPORT_APP"

  # Zip it for GitHub uploads/releases
  ditto -c -k --sequesterRsrc --keepParent "$EXPORT_APP" "$ZIP_PATH"

  echo "Exported app bundle:"
  echo "  $EXPORT_APP"
  echo "Created zip:"
  echo "  $ZIP_PATH"
}

build_app

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    lldb -- "$APP_BINARY"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$APP_NAME\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
    ;;
  --verify|verify)
    open_app
    sleep 1
    pgrep -x "$APP_NAME" >/dev/null
    ;;
  --export|export)
    export_app
    ;;
  *)
    echo "usage: $0 [run|debug|logs|telemetry|verify|export]" >&2
    exit 2
    ;;
esac
