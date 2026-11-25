"""Market structure: swing detection dan penentuan bias arah.

Bias ditentukan dari urutan swing high/low yang TERKONFIRMASI
(fractal dengan k candle kiri/kanan). Struktur ambigu -> bias neutral.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from bot.config.settings import settings
from bot.models.candle import Candle


@dataclass(frozen=True)
class SwingPoint:
    index: int
    price: float
    timestamp: datetime


@dataclass(frozen=True)
class MarketStructureResult:
    bias: str                    # "bullish" | "bearish" | "neutral"
    structure_label: str         # "HH+HL" | "LH+LL" | "ambiguous"
    swing_highs: tuple[SwingPoint, ...]
    swing_lows: tuple[SwingPoint, ...]
    last_swing_high: float | None
    last_swing_low: float | None
    range_high: float | None
    range_low: float | None


def find_swing_highs(candles: Sequence[Candle], k: int) -> list[SwingPoint]:
    """Swing high terkonfirmasi: high lebih tinggi dari k candle kiri & kanan."""
    result: list[SwingPoint] = []
    for i in range(k, len(candles) - k):
        hi = candles[i].high
        left_ok = all(candles[j].high < hi for j in range(i - k, i))
        right_ok = all(candles[j].high < hi for j in range(i + 1, i + k + 1))
        if left_ok and right_ok:
            result.append(SwingPoint(i, hi, candles[i].timestamp))
    return result


def find_swing_lows(candles: Sequence[Candle], k: int) -> list[SwingPoint]:
    """Swing low terkonfirmasi: low lebih rendah dari k candle kiri & kanan."""
    result: list[SwingPoint] = []
    for i in range(k, len(candles) - k):
        lo = candles[i].low
        left_ok = all(candles[j].low > lo for j in range(i - k, i))
        right_ok = all(candles[j].low > lo for j in range(i + 1, i + k + 1))
        if left_ok and right_ok:
            result.append(SwingPoint(i, lo, candles[i].timestamp))
    return result


def determine_bias(
    swing_highs: Sequence[SwingPoint],
    swing_lows: Sequence[SwingPoint],
) -> tuple[str, str]:
    """Klasifikasi struktur menjadi bias.

    Menggunakan dua swing terakhir per arah:
      - HH + HL -> bullish
      - LH + LL -> bearish
      - selainnya -> neutral (ambigu)
    """
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hh = swing_highs[-1].price > swing_highs[-2].price
        hl = swing_lows[-1].price > swing_lows[-2].price
        lh = swing_highs[-1].price < swing_highs[-2].price
        ll = swing_lows[-1].price < swing_lows[-2].price
        if hh and hl:
            return "bullish", "HH+HL"
        if lh and ll:
            return "bearish", "LH+LL"
    return "neutral", "ambiguous"


def analyze_market_structure(
    candles: Sequence[Candle],
    k: int | None = None,
) -> MarketStructureResult:
    """Analisis struktur market lengkap."""
    k = k if k is not None else settings.SWING_LEFT_RIGHT
    if len(candles) < 2 * k + 2:
        return MarketStructureResult(
            bias="neutral",
            structure_label="insufficient_data",
            swing_highs=(),
            swing_lows=(),
            last_swing_high=None,
            last_swing_low=None,
            range_high=None,
            range_low=None,
        )

    highs = find_swing_highs(candles, k)
    lows = find_swing_lows(candles, k)
    bias, label = determine_bias(highs, lows)

    last_high = highs[-1].price if highs else None
    last_low = lows[-1].price if lows else None

    # Range keseluruhan (untuk premium/discount)
    range_high = max(c.high for c in candles)
    range_low = min(c.low for c in candles)

    return MarketStructureResult(
        bias=bias,
        structure_label=label,
        swing_highs=tuple(highs),
        swing_lows=tuple(lows),
        last_swing_high=last_high,
        last_swing_low=last_low,
        range_high=range_high,
        range_low=range_low,
    )
