#!/usr/bin/env bash
# Start the image server on this machine (default port 8095). PYTHON may point at any interpreter that has the requirements.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m uvicorn server.app:app --host 127.0.0.1 --port "${PORT:-8095}"
