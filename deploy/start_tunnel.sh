#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="${1:-$PROJECT_ROOT/secrets/cloudflared_token.txt}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Install it first."
  exit 1
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Token file not found: $TOKEN_FILE"
  exit 1
fi

TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
if [[ -z "$TOKEN" ]]; then
  echo "Tunnel token file is empty: $TOKEN_FILE"
  exit 1
fi

cd "$PROJECT_ROOT"
exec cloudflared tunnel run --token "$TOKEN"
