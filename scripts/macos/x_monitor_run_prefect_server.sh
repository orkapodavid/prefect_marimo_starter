#!/bin/bash
set -euo pipefail

REPO_DIR="/Users/orbot/Developer/work/prefect_marimo_starter"

cd "$REPO_DIR"
source .venv/bin/activate

export PREFECT_API_URL="${PREFECT_API_URL:-http://127.0.0.1:4200/api}"

prefect server start

