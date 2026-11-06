#!/usr/bin/env bash
set -euo pipefail

export FASTLANE_OPT_OUT_USAGE=1

# Working directory is the current app directory (default: current working directory)
APP_DIR="${PWD}"
cd "${APP_DIR}"

# 1. Package Name Detection / Override
if [[ -z "${PACKAGE_NAME:-}" ]]; then
  for candidate in "app/build.gradle.kts" "automotive/build.gradle.kts" "build.gradle.kts"; do
    if [[ -f "$candidate" ]]; then
      PKG=$(grep -oE 'applicationId\s*=\s*"[^"]+"' "$candidate" | head -n1 | sed -E 's/.*"([^"]+)".*/\1/' || true)
      if [[ -n "$PKG" ]]; then
        PACKAGE_NAME="$PKG"
        break
      fi
    fi
  done
fi

PACKAGE_NAME="${PACKAGE_NAME:?Error: Provide a PACKAGE_NAME (e.g. set in mise.toml [env] or via PACKAGE_NAME=...)}"

# 2. Track (Default: automotive:internal)
TRACK="${TRACK:-automotive:internal}"

# 3. Locate AAB file
AAB_PATH="${AAB_PATH:-}"
if [[ -z "$AAB_PATH" && $# -gt 0 && "$1" == *.aab ]]; then
  AAB_PATH="$1"
  shift
fi

if [[ -z "$AAB_PATH" ]]; then
  # Auto-detect newest release AAB under standard build outputs
  AAB_PATH=$(find . -maxdepth 6 -type f -path "*/build/outputs/bundle/*Release/*.aab" ! -path "*/intermediates/*" 2>/dev/null | head -n1 || true)
fi

# Fallback default if not detected
DEFAULT_AAB="app/build/outputs/bundle/gmsAutomotiveUniversalRelease/app-gms-automotive-universal-release.aab"
AAB_PATH="${AAB_PATH:-$DEFAULT_AAB}"

if [[ ! -f "$AAB_PATH" ]]; then
  echo "❌ Error: AAB file not found at: $AAB_PATH"
  echo "👉 Build it first with: mise run bundle"
  exit 1
fi

# 4. Proguard / R8 mapping file (optional)
MAPPING_PATH="${MAPPING_PATH:-}"
if [[ -z "$MAPPING_PATH" ]]; then
  MAPPING_PATH=$(find . -maxdepth 6 -type f -path "*/build/outputs/mapping/*Release/mapping.txt" 2>/dev/null | head -n1 || true)
fi

# 5. Detect Service Account credentials
AUTH_ARGS=()

KEY_PATH="${SUPPLY_JSON_KEY:-${PLAY_STORE_JSON_KEY:-${GOOGLE_PLAY_KEY_FILE:-${GOOGLE_APPLICATION_CREDENTIALS:-${SA_KEY_FILE:-}}}}}"
KEY_PATH="${KEY_PATH%}"

KEY_DATA="${SUPPLY_JSON_KEY_DATA:-${PLAY_STORE_JSON_KEY_DATA:-${GOOGLE_PLAY_KEY_DATA:-${SA_KEY_DATA:-}}}}"

GENERIC_TOKEN="${SA_TOKEN:-${PLAY_TOKEN:-${GOOGLE_PLAY_KEY:-}}}"
if [[ -n "$GENERIC_TOKEN" ]]; then
  if [[ -f "$GENERIC_TOKEN" ]]; then
    KEY_PATH="$GENERIC_TOKEN"
  elif [[ "$GENERIC_TOKEN" =~ ^[[:space:]]*\{ ]]; then
    KEY_DATA="$GENERIC_TOKEN"
  fi
fi

if [[ -n "$KEY_DATA" ]]; then
  AUTH_ARGS+=(--json_key_data "$KEY_DATA")
elif [[ -n "$KEY_PATH" && -f "$KEY_PATH" ]]; then
  AUTH_ARGS+=(--json_key "$KEY_PATH")
else
  echo "❌ Error: Google Play Service Account credentials not found in environment."
  echo ""
  echo "Please provide credentials via PLAY_STORE_JSON_KEY_DATA or PLAY_STORE_JSON_KEY."
  exit 1
fi

EXTRA_ARGS=()
if [[ -n "$MAPPING_PATH" && -f "$MAPPING_PATH" ]]; then
  echo "📄 Found mapping file: $MAPPING_PATH"
  EXTRA_ARGS+=(--mapping "$MAPPING_PATH")
fi

echo "🚀 Uploading to Google Play track '$TRACK'..."
echo "📦 Package: $PACKAGE_NAME"
echo "📦 AAB:     $AAB_PATH"

fastlane supply \
  --package_name "$PACKAGE_NAME" \
  --track "$TRACK" \
  --aab "$AAB_PATH" \
  "${AUTH_ARGS[@]}" \
  "${EXTRA_ARGS[@]}" \
  --skip_upload_metadata true \
  --skip_upload_changelogs true \
  --skip_upload_images true \
  --skip_upload_screenshots true \
  "$@"

echo "✅ Successfully released to '$TRACK' track!"
