from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def write_report(summary: pd.DataFrame, trades: pd.DataFrame, settings_path: str, output_root: str | Path = "output/backtests") -> Path:
    run_dir = Path(output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(run_dir / "summary.csv", index=False)
    trades.to_csv(run_dir / "trades.csv", index=False)
    if not trades.empty and "result_r" in trades:
        completed = trades.loc[trades["result_r"].notna()].copy()
        if not completed.empty:
            keys = ["grid_symbol", "grid_model", "grid_bias"]
            rankings = completed.groupby(keys)["result_r"].mean().sort_values(ascending=False).head(5)
            for rank, key in enumerate(rankings.index, start=1):
                group = completed.loc[(completed[keys] == key).all(axis=1)].copy()
                group = group.sort_values("close_time")
                figure, axis = plt.subplots(figsize=(9, 4.5))
                axis.plot(range(1, len(group) + 1), group["result_r"].astype(float).cumsum())
                axis.set(title=f"{' · '.join(key)}", xlabel="Completed trade", ylabel="Cumulative R")
                axis.grid(alpha=0.2)
                figure.tight_layout()
                figure.savefig(run_dir / f"equity_curve_{rank}.png", dpi=120)
                plt.close(figure)
    lines = ["# ICT/SMC Backtest Report", "", f"Settings: `{settings_path}`", "", "## Ranking", ""]
    if summary.empty:
        lines.append("No completed trades were produced.")
    else:
        lines.append(summary.to_markdown(index=False))
        lines.extend(["", "> Results with fewer than 50 trades are flagged as statistically weak."])
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return run_dir
