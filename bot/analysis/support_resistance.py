"""Support / Resistance level detection.

Level horizontal dihasilkan dari pengelompokan (clustering) titik swing
high/low yang berdekatan. Semakin banyak sentuhan, semakin kuat level.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bot.analysis.market_structure import SwingPoint


@dataclass(frozen=True)
class Level:
    price: float
    kind: str     # "support" | "resistance"
    touches: int


def _cluster(prices: list[float], tolerance: float) -> list[tuple[float, int]]:
    """Greedy clustering: kembalikan (rata-rata harga, jumlah anggota)."""
    if not prices:
        return []
    prices = sorted(prices)
    clusters: list[tuple[float, int]] = []
    current_sum = prices[0]
    current_count = 1
    current_anchor = prices[0]
    for p in prices[1:]:
        if abs(p - current_anchor) <= tolerance:
            current_sum += p
            current_count += 1
        else:
            clusters.append((current_sum / current_count, current_count))
            current_sum = p
            current_count = 1
            current_anchor = p
    clusters.append((current_sum / current_count, current_count))
    return clusters


def detect_levels(
    swing_highs: Sequence[SwingPoint],
    swing_lows: Sequence[SwingPoint],
    tolerance_ratio: float = 0.003,
) -> list[Level]:
    """Deteksi level support/resistance dari swing points."""
    if not swing_highs and not swing_lows:
        return []

    ref_price = 1.0
    all_prices = [s.price for s in swing_highs] + [s.price for s in swing_lows]
    if all_prices:
        ref_price = max(all_prices)

    tolerance = tolerance_ratio * ref_price

    levels: list[Level] = []
    for price, touches in _cluster([s.price for s in swing_lows], tolerance):
        levels.append(Level(price, "support", touches))
    for price, touches in _cluster([s.price for s in swing_highs], tolerance):
        levels.append(Level(price, "resistance", touches))

    levels.sort(key=lambda L: L.price)
    return levels
