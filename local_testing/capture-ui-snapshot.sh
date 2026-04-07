#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ssh-target> [remote-base-url] [day]" >&2
  echo "Example: $0 user@example-host http://127.0.0.1:5000 2026-04-04" >&2
  exit 1
fi

SSH_TARGET="$1"
REMOTE_BASE_URL="${2:-http://127.0.0.1:5000}"
DAY="${3:-$(date +%F)}"
MONTH="${DAY%-*}"
YEAR="${DAY%%-*}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/site/mock"
OUTPUT_JSON="${OUTPUT_DIR}/ui-snapshot.json"
OUTPUT_CSV="${OUTPUT_DIR}/ui-snapshot.csv"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

mkdir -p "${OUTPUT_DIR}"

fetch_remote_json() {
  local remote_path="$1"
  local output_file="$2"
  ssh "${SSH_TARGET}" "curl -fsS '${REMOTE_BASE_URL}${remote_path}'" > "${output_file}"
}

echo "Capturing UI snapshot from ${SSH_TARGET} (${REMOTE_BASE_URL}) for ${DAY}"

fetch_remote_json "/api/overview" "${TMP_DIR}/overview.json"
fetch_remote_json "/api/date-bounds" "${TMP_DIR}/dates.json"
fetch_remote_json "/api/chart/live?hours=24" "${TMP_DIR}/realtime_24.json"
fetch_remote_json "/api/period?bucket=day&date=${DAY}" "${TMP_DIR}/day.json"
fetch_remote_json "/api/period?bucket=month&date=${MONTH}" "${TMP_DIR}/month.json"
fetch_remote_json "/api/period?bucket=year&date=${YEAR}" "${TMP_DIR}/year.json"
fetch_remote_json "/api/period?bucket=all" "${TMP_DIR}/all_time.json"
fetch_remote_json "/api/breakdown?bucket=day&prefix=${MONTH}" "${TMP_DIR}/days_in_month.json"
fetch_remote_json "/api/breakdown?bucket=month&prefix=${YEAR}" "${TMP_DIR}/months_in_year.json"
fetch_remote_json "/api/breakdown?bucket=year" "${TMP_DIR}/years_in_all_time.json"
fetch_remote_json "/api/statistics" "${TMP_DIR}/statistics.json"

ssh "${SSH_TARGET}" "curl -fsS '${REMOTE_BASE_URL}/api/csv?bucket=day&prefix=${DAY}'" > "${OUTPUT_CSV}"

python3 - "${TMP_DIR}" "${OUTPUT_JSON}" "${DAY}" "${MONTH}" "${YEAR}" <<'PY'
import json
import pathlib
import sys

tmp_dir = pathlib.Path(sys.argv[1])
output_json = pathlib.Path(sys.argv[2])
day = sys.argv[3]
month = sys.argv[4]
year = sys.argv[5]

def load(name):
    return json.loads((tmp_dir / name).read_text(encoding="utf-8"))

snapshot = {
    "meta": {
        "label": "Captured sample snapshot",
        "captured_at": load("overview.json").get("recorded_at") or "",
    },
    "name": "PiPhocos",
    "apiOverview": load("overview.json"),
    "dates": load("dates.json"),
    "realTime": {
        "24": load("realtime_24.json")["series"],
    },
    "historical": {
        "days": {
            day: load("day.json"),
        },
        "months": {
            month: load("month.json"),
        },
        "years": {
            year: load("year.json"),
        },
        "all_time": {
            "all_time": load("all_time.json"),
        },
    },
    "historyDetails": {
        "days_in_month": {
            month: load("days_in_month.json")["items"],
        },
        "months_in_year": {
            year: load("months_in_year.json")["items"],
        },
        "years_in_all_time": load("years_in_all_time.json")["items"],
    },
    "statistics": load("statistics.json"),
}

output_json.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY

echo "Wrote ${OUTPUT_JSON}"
echo "Wrote ${OUTPUT_CSV}"
echo "Open http://127.0.0.1:4173/?mock=1 after running ./local_testing/run-ui-mock.sh"
