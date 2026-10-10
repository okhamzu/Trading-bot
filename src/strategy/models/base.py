from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain import Setup
from src.strategy.context import MarketContext


class EntryModel(ABC):
    name: str

    @abstractmethod
    def scan(self, ctx: MarketContext) -> list[Setup]:
        raise NotImplementedError
