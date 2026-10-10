from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskGuards:
    max_daily_loss_pct: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    starting_balance: float
    peak_equity: float = 0
    consecutive_losses: int = 0
    daily_pnl: dict[date, float] = field(default_factory=dict)
    manually_halted: bool = False

    def __post_init__(self) -> None:
        self.peak_equity = self.peak_equity or self.starting_balance

    def update(self, day: date, pnl: float, equity: float) -> None:
        self.daily_pnl[day] = self.daily_pnl.get(day, 0.0) + pnl
        self.peak_equity = max(self.peak_equity, equity)
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def allowed(self, day: date, equity: float) -> tuple[bool, str]:
        self.peak_equity = max(self.peak_equity, equity)
        if self.manually_halted:
            return False, "Manual/max-drawdown halt requires reset"
        if -self.daily_pnl.get(day, 0.0) >= self.starting_balance * self.max_daily_loss_pct / 100:
            return False, "Daily loss limit reached"
        drawdown = (self.peak_equity - equity) / self.peak_equity * 100 if self.peak_equity else 0
        if drawdown >= self.max_drawdown_pct:
            self.manually_halted = True
            return False, "Maximum drawdown halt triggered"
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, "Consecutive-loss limit reached"
        return True, "Risk guards allow new setups"

    def reset_halt(self) -> None:
        self.manually_halted = False
        self.consecutive_losses = 0
