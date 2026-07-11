#!/bin/sh
set -eu

API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:8000}"

cat > /usr/share/nginx/html/config.js <<EOF
window.__MARKETLENS_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL}",
};
EOF
