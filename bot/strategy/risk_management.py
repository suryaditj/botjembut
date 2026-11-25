"""Risk management: Entry, Stop Loss, Take Profit, Risk/Reward.

SL dan TP dibangun dari STRUKTUR harga (bukan jarak tetap):
  - BUY : SL di bawah struktur invalidasi (zona / swing low) + buffer ATR,
          TP1 & TP2 pada resistance/liquidity terdekat di atas.
  - SELL: kebalikannya.

RR minimum wajib 1:2; jika tidak terpenuhi -> plan tidak valid (WAIT).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bot.config.settings import settings
from bot.models.candle import Candle


@dataclass(frozen=True)
class TradePlan:
    direction: str
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    rr1: float
    rr2: float
    valid: bool
    reason: str = ""


def atr(candles: Sequence[Candle], period: int = 14) -> float:
    """Average True Range."""
    trs: list[float] = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i].high - candles[i].low,
            abs(candles[i].high - candles[i - 1].close),
            abs(candles[i].low - candles[i - 1].close),
        )
        trs.append(tr)
    if not trs:
        return 0.0
    if len(trs) < period:
        return sum(trs) / len(trs)
    return sum(trs[-period:]) / period


def build_trade_plan(
    direction: str,
    entry: float,
    structure_level: float,
    targets: Sequence[float],
    atr_value: float,
    min_rr: float | None = None,
) -> TradePlan:
    """Bangun rencana trading dari struktur.

    - direction: "buy" | "sell"
    - entry: harga entry (close candle konfirmasi)
    - structure_level: level struktur untuk SL (di bawah untuk buy, di atas untuk sell)
    - targets: daftar level target (resistance untuk buy, support untuk sell),
      diurutkan naik.
    """
    min_rr = min_rr if min_rr is not None else settings.MIN_RISK_REWARD
    buffer = atr_value * settings.SL_BUFFER_ATR

    if buffer <= 0:
        return TradePlan(direction, entry, 0, 0, 0, 0, 0, False, "ATR = 0, tidak bisa menghitung buffer SL.")

    if direction == "buy":
        sl = structure_level - buffer
        if sl >= entry:
            return TradePlan(direction, entry, sl, 0, 0, 0, 0, False, "SL tidak di bawah entry.")
        tps = sorted(t for t in targets if t > entry)
        if len(tps) < 2:
            return TradePlan(direction, entry, sl, 0, 0, 0, 0, False, "Target struktur tidak cukup (butuh TP1 & TP2).")
        tp1, tp2 = tps[0], tps[1]
    else:
        sl = structure_level + buffer
        if sl <= entry:
            return TradePlan(direction, entry, sl, 0, 0, 0, 0, False, "SL tidak di atas entry.")
        tps = sorted((t for t in targets if t < entry), reverse=True)
        if len(tps) < 2:
            return TradePlan(direction, entry, sl, 0, 0, 0, 0, False, "Target struktur tidak cukup (butuh TP1 & TP2).")
        tp1, tp2 = tps[0], tps[1]

    risk = abs(entry - sl)
    if risk <= 0:
        return TradePlan(direction, entry, sl, tp1, tp2, 0, 0, False, "Risk = 0.")

    rr1 = abs(tp1 - entry) / risk
    rr2 = abs(tp2 - entry) / risk

    if rr1 < min_rr:
        return TradePlan(
            direction, entry, sl, tp1, tp2, rr1, rr2, False,
            f"RR1 ({rr1:.2f}) di bawah minimum 1:{min_rr:.0f}.",
        )

    return TradePlan(direction, entry, sl, tp1, tp2, rr1, rr2, True, "")
