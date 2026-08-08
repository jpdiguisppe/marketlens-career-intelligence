#!/bin/sh
set -eu
umask 027

API_BASE_URL="$(printf '%s' "${VITE_API_BASE_URL:-http://localhost:8000}" | tr -d '\r\n')"
case "$API_BASE_URL" in
  http://*|https://*) ;;
  *) API_BASE_URL="http://localhost:8000" ;;
esac

API_ORIGIN="$(printf '%s' "$API_BASE_URL" | sed -E 's#^(https?://[^/]+).*$#\1#')"
if ! printf '%s' "$API_ORIGIN" | grep -Eq '^https?://[A-Za-z0-9._:-]+$'; then
  API_BASE_URL="http://localhost:8000"
  API_ORIGIN="http://localhost:8000"
fi

SAFE_API_BASE_URL="$(printf '%s' "$API_BASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')"

DEPLOYMENT_REVISION="$(printf '%s' "${RAILWAY_GIT_COMMIT_SHA:-}" | tr -cd '0-9a-fA-F' | cut -c1-40)"
if [ "${#DEPLOYMENT_REVISION}" -ne 40 ]; then
  DEPLOYMENT_REVISION="unknown"
else
  DEPLOYMENT_REVISION="$(printf '%s' "$DEPLOYMENT_REVISION" | tr 'A-F' 'a-f')"
fi

PORT_VALUE="${PORT:-8080}"
case "$PORT_VALUE" in
  ''|*[!0-9]*) PORT_VALUE="8080" ;;
esac
if [ "$PORT_VALUE" -lt 1024 ] || [ "$PORT_VALUE" -gt 65535 ]; then
  PORT_VALUE="8080"
fi

cat > /usr/share/nginx/html/config.js <<EOF
window.__MARKETLENS_CONFIG__ = {
  apiBaseUrl: "${SAFE_API_BASE_URL}",
  deploymentRevision: "${DEPLOYMENT_REVISION}",
};
EOF

sed \
  -e "s|__PORT__|${PORT_VALUE}|g" \
  -e "s|__API_ORIGIN__|${API_ORIGIN}|g" \
  /etc/nginx/nginx.conf.template > /tmp/nginx.conf

exec nginx -c /tmp/nginx.conf -g 'daemon off;'
