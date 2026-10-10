#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-cloud.txt
.venv/bin/python -m pytest -q
printf '\nTrading bot environment ready. Backtests run here; live MT5 requires Windows.\n'
