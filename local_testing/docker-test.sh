#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "Building Docker image"
docker image build -t piphocos:local .

echo "Running Docker image on http://127.0.0.1:5000"
docker container run --rm -p 5000:5000 -v "$(pwd)/data:/data" piphocos:local
