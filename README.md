# Browser development workspace

This repository currently contains cloud setup files only; the trading bot has not been imported.

## Start

Open https://codespaces.new/okhamzu/Trading-bot and create a Codespace on main. Check the displayed usage/billing information first. Wait for the setup command to finish. Open Terminal > New Terminal and run:

```bash
claude
```

Complete Claude's sign-in in your browser using an eligible Claude account. A ChatGPT subscription does not include Claude access.

Python 3.11, a project virtual environment, Node.js, pandas, NumPy, matplotlib, requests, python-dotenv, pytest and Jupyter kernel support are configured. Claude Code is installed using Anthropic's official native installer. Setup checks imports and the Claude version. If setup fails, review the creation log and rerun `bash .devcontainer/setup.sh`.

## Bring in your project

Before importing private bot code, make sure the repository visibility is appropriate. Never commit passwords, API keys or broker credentials. The ignore file is a precaution, not a secret scanner. Add your actual bot dependencies after reviewing compatibility; requirements-cloud.txt is only a starter toolset.

Use this Linux workspace for editing, analysis and CSV-based backtesting. MetaTrader 5 terminal connectivity is not configured here. Run the MT5-dependent portion on a separate Windows computer or Windows VPS. No trading, WhatsApp integration, VPS or broker connection is activated by this setup.

Stop the Codespace when finished via https://github.com/codespaces. Cloud compute and storage may incur charges depending on your account allowance.

Official documentation:
- https://code.claude.com/docs/en/setup
- https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/setting-up-your-python-project-for-codespaces
