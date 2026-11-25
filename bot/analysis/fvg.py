"""Fair Value Gap (FVG) detection.

FVG terbentuk dari ketidakseimbangan 3 candle:
  - Bullish FVG: candle ke-3 low lebih tinggi dari candle ke-1 high.
  - Bearish FVG: candle ke-3 high lebih rendah dari candle ke-1 low.
Zona FVG = celah antar candle ke-1 dan ke-3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bot.models.candle import Candle


@dataclass(frozen=True)
class FVG:
    direction: str      # "bullish" | "bearish"
    top: float
    bottom: float
    index: int          # index candle tengah (ke-2 dari 3)
    status: str         # "unmitigated" | "mitigated"


def detect_fvgs(candles: Sequence[Candle]) -> list[FVG]:
    """Deteksi semua FVG pada deret candle."""
    fvgs: list[FVG] = []
    if len(candles) < 3:
        return fvgs

    for i in range(1, len(candles) - 1):
        first = candles[i - 1]
        third = candles[i + 1]

        if third.low > first.high:
            fvgs.append(
                FVG(
                    direction="bullish",
                    top=third.low,
                    bottom=first.high,
                    index=i,
                    status="unmitigated",
                )
            )
        elif third.high < first.low:
            fvgs.append(
                FVG(
                    direction="bearish",
                    top=first.low,
                    bottom=third.high,
                    index=i,
                    status="unmitigated",
                )
            )

    return _update_status(candles, fvgs)


def _update_status(candles: Sequence[Candle], fvgs: list[FVG]) -> list[FVG]:
    """Tandai FVG yang sudah dimitigasi (harga kembali memasuki zona)."""
    updated: list[FVG] = []
    for fvg in fvgs:
        status = "unmitigated"
        for c in candles[fvg.index + 2:]:
            if fvg.direction == "bullish" and c.low <= fvg.top:
                status = "mitigated"
                break
            if fvg.direction == "bearish" and c.high >= fvg.bottom:
                status = "mitigated"
                break
        updated.append(FVG(fvg.direction, fvg.top, fvg.bottom, fvg.index, status))
    return updated
