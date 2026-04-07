#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"
docker compose --profile ui-dev up -d piphocos-ui-dev
echo "UI dev Docker is running on http://127.0.0.1:4173/?mock=1"
