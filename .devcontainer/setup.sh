#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-cloud.txt
curl -fsSL https://claude.ai/install.sh | bash
"$HOME/.local/bin/claude" --version
.venv/bin/python -c 'import pandas, numpy, matplotlib, requests, dotenv; print("Python tools ready")'
printf '\nSetup complete. Open a new terminal and run: claude\n'
