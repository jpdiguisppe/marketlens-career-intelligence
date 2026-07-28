#!/bin/sh
set -eu

API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:8000}"
DEPLOYMENT_REVISION="$(printf '%s' "${RAILWAY_GIT_COMMIT_SHA:-}" | tr -cd '0-9a-fA-F' | cut -c1-40)"

if [ "${#DEPLOYMENT_REVISION}" -ne 40 ]; then
  DEPLOYMENT_REVISION="unknown"
else
  DEPLOYMENT_REVISION="$(printf '%s' "$DEPLOYMENT_REVISION" | tr 'A-F' 'a-f')"
fi

cat > /usr/share/nginx/html/config.js <<EOF
window.__MARKETLENS_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL}",
  deploymentRevision: "${DEPLOYMENT_REVISION}",
};
EOF
