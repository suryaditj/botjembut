"""Liquidity pool dan liquidity sweep.

Liquidity pool: area di mana stop loss / order berkerumun, biasanya di
sekitar swing high (buy-side, di atas) dan swing low (sell-side, di bawah).

Liquidity sweep: harga menggerus (wick) melewati level lalu menutup kembali
di sisi lain — pola perburuan stop (stop hunt).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from bot.analysis.market_structure import SwingPoint
from bot.models.candle import Candle


@dataclass(frozen=True)
class LiquidityPool:
    price: float
    side: str        # "buy_side" | "sell_side"
    touches: int


def detect_liquidity_pools(
    swing_highs: Sequence[SwingPoint],
    swing_lows: Sequence[SwingPoint],
    tolerance_ratio: float = 0.002,
) -> list[LiquidityPool]:
    """Klaster swing high/low menjadi liquidity pool."""
    pools: list[LiquidityPool] = []

    highs = [s.price for s in swing_highs]
    lows = [s.price for s in swing_lows]
    ref = 1.0
    if highs or lows:
        ref = max(highs + lows, default=1.0)
    tol = tolerance_ratio * ref

    # Buy-side liquidity: klaster swing high (stop di atas)
    if highs:
        highs_sorted = sorted(highs)
        run = [highs_sorted[0]]
        for p in highs_sorted[1:]:
            if p - run[0] <= tol:
                run.append(p)
            else:
                pools.append(LiquidityPool(sum(run) / len(run), "buy_side", len(run)))
                run = [p]
        pools.append(LiquidityPool(sum(run) / len(run), "buy_side", len(run)))

    # Sell-side liquidity: klaster swing low (stop di bawah)
    if lows:
        lows_sorted = sorted(lows)
        run = [lows_sorted[0]]
        for p in lows_sorted[1:]:
            if p - run[0] <= tol:
                run.append(p)
            else:
                pools.append(LiquidityPool(sum(run) / len(run), "sell_side", len(run)))
                run = [p]
        pools.append(LiquidityPool(sum(run) / len(run), "sell_side", len(run)))

    pools.sort(key=lambda p: p.price)
    return pools


def detect_liquidity_sweep(
    candles: Sequence[Candle],
    level: float,
    direction: str,
) -> bool:
    """Deteksi sweep pada candle terakhir.

    - direction="bullish": low menembus level (sell-side) lalu close di atas level.
    - direction="bearish": high menembus level (buy-side) lalu close di bawah level.
    """
    if not candles:
        return False
    c = candles[-1]

    if direction == "bullish":
        return c.low < level and c.close > level
    if direction == "bearish":
        return c.high > level and c.close < level
    return False


def nearest_pool(pools: Sequence[LiquidityPool], price: float, side: str) -> Optional[LiquidityPool]:
    """Pool terdekat pada sisi tertentu relatif terhadap harga."""
    candidates = [p for p in pools if p.side == side]
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p.price - price))
