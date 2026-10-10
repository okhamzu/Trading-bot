# ICT/SMC Trading Alert Bot

An alerts-only Python 3.11+ scanner and no-lookahead backtester for XAUUSD and major FX pairs. It connects to a logged-in MetaTrader 5 terminal, evaluates only closed candles, finds ICT/SMC setups, sizes them at configured risk, and sends the owner a manual-trade alert. **It cannot place orders.**

## Safety guarantees

- `mode.dry_run` must be `true`; startup fails otherwise.
- There is no live execution module and no MT5 order-placement call.
- The latest forming MT5 candle is discarded.
- Historical higher-timeframe data is exposed only after the candle closes.
- Credentials and generated trading data are gitignored.

## Install

Live MT5 access requires Windows, MetaTrader 5 installed and logged in, and Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` locally. Never commit it. Review `config/settings.yaml`; broker symbol names may use suffixes such as `XAUUSDm`.

## First run

In MT5, set **Tools → Options → Charts → Max bars in chart** to Unlimited and load the required history.

```bash
python scripts/export_candles.py --symbol XAUUSD --tf M15 --bars 500
python scripts/download_history.py --start 2025-01-01 --symbols XAUUSD EURUSD
python scripts/run_backtest.py --model sweep_mss_fvg --bias htf_structure --symbol XAUUSD
python scripts/run_backtest.py --grid all
python scripts/run_live.py --once
python scripts/run_live.py
```

`export_candles.py` writes `time_utc, time_pkt, open, high, low, close, volume` to `output/exports/` for manual analysis. Backtests read the cached Parquet files and therefore run without MT5, including on macOS/Linux.

## Architecture

- `src/analysis/`: deterministic ATR, swings, structure, liquidity, FVG, OB, ranges, displacement and sessions.
- `src/strategy/`: bias methods, reusable filters and entry models.
- `src/backtest/`: event-driven execution, conservative fills, metrics and reports.
- `src/alerts/`, `src/charts/`, `src/ai/`: WhatsApp formatting/delivery, annotated charts and optional Claude commentary.
- `src/state/`, `src/journal/`, `src/tracking/`: restart-safe dedupe and setup outcome tracking.

The live path and backtester call the same `build_context()` and `scan_context()` functions.

## WhatsApp

`dry_run: true` logs alerts instead of sending them. Provider adapters exist for Twilio, CallMeBot and Meta Cloud. Twilio accepts text immediately, but a local chart needs a public media URL; the adapter safely falls back to text rather than exposing files. Meta Cloud can be extended to upload the generated chart directly.

## Backtest outputs

Each run writes `summary.csv`, `trades.csv`, and `report.md` under a timestamped folder in `output/backtests/`. The grid always supports the `none` bias baseline and marks results with fewer than 50 trades as weak.

## Disclaimer

This software is a research and alerting tool, not financial advice. Validate every model with out-of-sample testing and demo forward testing before risking real money.

## Development and verification

Codex can edit this repository without Claude Code. Codespaces setup installs the bot dependencies and runs the tests. Activate `.venv/bin/activate` for terminal work. Live MT5 still requires Windows.

Run `python -m pytest -q -W error` to verify the data feeds, strategy components, risk sizing, fill costs, dry-run behavior and state storage. GitHub Actions runs these tests on Linux and Windows with Python 3.11 and 3.12.

The portable cache is `data/history/`: `{symbol}_{timeframe}.parquet` (CSV fallback) and `symbol_specs.json`. Candle times are UTC opening times; feeds compute close times and exclude candles that have not closed.

Dry-run mode logs WhatsApp messages locally. External delivery and MT5 connectivity need separate integration testing. The tests do not establish profitability or guarantee the absence of every defect.
