"""Model candle yang sudah dinormalisasi.

Candle selalu dianggap TERTUTUP kecuali `is_closed=False`.
Sinyal hanya boleh dibangun dari candle tertutup (anti-repaint).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    is_closed: bool = True

    @property
    def bullish(self) -> bool:
        return self.close >= self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def range(self) -> float:
        return self.high - self.low

    def is_valid(self) -> bool:
        """Validasi dasar satu candle."""
        if not (self.high >= self.low):
            return False
        if not (self.high >= self.open and self.high >= self.close):
            return False
        if not (self.low <= self.open and self.low <= self.close):
            return False
        if self.open <= 0 or self.close <= 0:
            return False
        return True
