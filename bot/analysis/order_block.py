"""Order Block (OB) detection.

OB = candle berlawanan warna TERAKHIR sebelum pergerakan impulsif
(displacement) yang kuat:
  - Bullish OB: candle bearish sebelum pergerakan naik impulsif.
  - Bearish OB: candle bullish sebelum pergerakan turun impulsif.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bot.models.candle import Candle


@dataclass(frozen=True)
class OrderBlock:
    direction: str      # "bullish" | "bearish"
    top: float
    bottom: float
    index: int
    status: str         # "fresh" | "mitigated" | "invalidated"


def detect_order_blocks(
    candles: Sequence[Candle],
    displacement_mult: float = 1.5,
) -> list[OrderBlock]:
    if len(candles) < 2:
        return []

    avg_body = sum(c.body for c in candles) / len(candles)
    threshold = displacement_mult * avg_body if avg_body > 0 else float("inf")

    blocks: list[OrderBlock] = []
    for i in range(1, len(candles)):
        dep = candles[i]
        prev = candles[i - 1]
        if dep.body <= threshold:
            continue
        if dep.bullish and prev.bearish:
            blocks.append(
                OrderBlock("bullish", prev.high, prev.low, i - 1, "fresh")
            )
        elif dep.bearish and prev.bullish:
            blocks.append(
                OrderBlock("bearish", prev.high, prev.low, i - 1, "fresh")
            )

    return _update_status(candles, blocks)


def _update_status(candles: Sequence[Candle], blocks: list[OrderBlock]) -> list[OrderBlock]:
    updated: list[OrderBlock] = []
    for ob in blocks:
        status = "fresh"
        for c in candles[ob.index + 2:]:
            if ob.direction == "bullish":
                if c.low <= ob.top:  # harga kembali ke zona
                    status = "mitigated"
                if c.close < ob.bottom:  # tembus ke bawah -> invalid
                    status = "invalidated"
                    break
            else:
                if c.high >= ob.bottom:
                    status = "mitigated"
                if c.close > ob.top:
                    status = "invalidated"
                    break
        updated.append(OrderBlock(ob.direction, ob.top, ob.bottom, ob.index, status))
    return updated
