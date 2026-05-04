#!/bin/sh
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: build_backend_vendor.sh <requirements.txt> <vendor-dir>" >&2
  exit 64
fi

REQUIREMENTS_FILE="$1"
VENDOR_DIR="$2"
STAMP_FILE="$VENDOR_DIR/.requirements.sha256"

find_python() {
  if [ "${CHOROQ_BHE_BUILD_PYTHON:-}" != "" ]; then
    printf '%s\n' "$CHOROQ_BHE_BUILD_PYTHON"
    return 0
  fi

  for candidate in \
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3" \
    "$(command -v python3)" \
    "/usr/bin/python3"; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1 && "$candidate" -m pip --version >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python 3.10+ with pip is required to vendor backend dependencies. Set CHOROQ_BHE_BUILD_PYTHON to a suitable interpreter." >&2
  exit 69
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "Missing backend requirements file: $REQUIREMENTS_FILE" >&2
  exit 66
fi

REQUIREMENTS_HASH="$(/usr/bin/shasum -a 256 "$REQUIREMENTS_FILE" | /usr/bin/awk '{print $1}')"
if [ -f "$STAMP_FILE" ] && [ "$(/bin/cat "$STAMP_FILE")" = "$REQUIREMENTS_HASH" ]; then
  /bin/echo "$PYTHON_BIN" > "$VENDOR_DIR/.python-executable"
  exit 0
fi

TMP_VENDOR="$VENDOR_DIR.tmp"
/bin/rm -rf "$TMP_VENDOR"
/bin/mkdir -p "$TMP_VENDOR"

"$PYTHON_BIN" -m pip install \
  --disable-pip-version-check \
  --no-input \
  --upgrade \
  --target "$TMP_VENDOR" \
  -r "$REQUIREMENTS_FILE"

/bin/rm -rf "$VENDOR_DIR"
/bin/mv "$TMP_VENDOR" "$VENDOR_DIR"
/bin/echo "$REQUIREMENTS_HASH" > "$STAMP_FILE"
/bin/echo "$PYTHON_BIN" > "$VENDOR_DIR/.python-executable"
/usr/bin/xattr -cr "$VENDOR_DIR" || true
