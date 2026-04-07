#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-4173}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Serving UI mock on http://127.0.0.1:${PORT}/?mock=1"
cd "${PROJECT_ROOT}"
python3 local_testing/ui_mock_server.py --port "${PORT}" --directory site
