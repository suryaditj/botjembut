"""Mesin multi-timeframe (H4 + H1 + M15).

Urutan analisis wajib:
  1. Ambil data H4, H1, M15 (sudah divalidasi & tertutup).
  2. Tentukan bias H4.
  3. Identifikasi zona H1.
  4. Pilih zona yang searah dengan bias H4.
  5. Tunggu harga memasuki zona.
  6. Periksa konfirmasi M15.
  7. Validasi seluruh syarat entry.
  8. Hitung Entry, SL, TP, RR.
  9. Tentukan keputusan akhir.

Timeframe kecil TIDAK boleh mengabaikan arah timeframe utama.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from bot.analysis.bos_choch import detect_bos_choch
from bot.analysis.market_structure import analyze_market_structure
from bot.analysis.premium_discount import compute_premium_discount
from bot.analysis.supply_demand import Zone, active_zones, detect_zones
from bot.analysis.support_resistance import detect_levels
from bot.models.candle import Candle
from bot.strategy.entry_confirmation import (
    ConfirmationResult,
    check_entry_confirmation,
    is_rejection_candle,
)
from bot.strategy.risk_management import TradePlan, atr, build_trade_plan
from bot.strategy.scoring import ScoreInput, score_signal


@dataclass(frozen=True)
class MultiTFResult:
    symbol: str
    signal: str                      # "BUY" | "SELL" | "WAIT"
    h4_bias: str
    h4_structure: str
    h4_bos: Optional[str]
    h4_choch: Optional[str]
    h1_zone: Optional[Zone] = None
    price_in_zone: bool = False
    m15_sweep: bool = False
    m15_rejection: bool = False
    m15_choch: Optional[str] = None
    m15_displacement: bool = False
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    risk_reward: Optional[float] = None
    score: Optional[int] = None
    quality: str = ""
    reasons: list[str] = field(default_factory=list)
    invalidation: str = ""
    premium_discount: str = ""


def _is_displacement(candles: Sequence[Candle], direction: str) -> bool:
    if len(candles) < 3:
        return False
    avg_body = sum(c.body for c in candles) / len(candles)
    last = candles[-1]
    if avg_body <= 0:
        return False
    if direction == "buy" and last.bullish and last.body > avg_body * 1.5:
        return True
    if direction == "sell" and last.bearish and last.body > avg_body * 1.5:
        return True
    return False


def analyze_symbol(
    symbol: str,
    h4_candles: Sequence[Candle],
    h1_candles: Sequence[Candle],
    m15_candles: Sequence[Candle],
) -> MultiTFResult:
    """Jalankan analisis multi-timeframe penuh untuk satu simbol."""
    reasons: list[str] = []
    current_price = m15_candles[-1].close if m15_candles else None
    if current_price is None:
        return MultiTFResult(symbol, "WAIT", "neutral", "", None, None,
                             reasons=["Tidak ada data harga."])

    # --- 1. H4 bias ---
    h4 = analyze_market_structure(h4_candles)
    h4_bos_choch = detect_bos_choch(
        h4_candles, h4.bias, h4.last_swing_high, h4.last_swing_low
    )

    # --- 2 & 3. Zona H1 searah bias ---
    zones = detect_zones(h1_candles)
    if h4.bias == "bullish":
        direction = "buy"
        zone_kind = "demand"
    elif h4.bias == "bearish":
        direction = "sell"
        zone_kind = "supply"
    else:
        return MultiTFResult(
            symbol, "WAIT", "neutral", h4.structure_label,
            h4_bos_choch.bos, h4_bos_choch.choch,
            reasons=["Struktur H4 ambigu (bukan HH+HL atau LH+LL)."],
            invalidation="Tidak ada bias arah yang valid di H4.",
        )

    active = active_zones(zones, zone_kind)
    zone = next((z for z in active if z.bottom <= current_price <= z.top), None)
    price_in_zone = zone is not None

    # --- 4-6. Konfirmasi M15 ---
    m15_last = m15_candles[-1]
    m15_struct = analyze_market_structure(m15_candles)
    m15_bos_choch = detect_bos_choch(
        m15_candles, m15_struct.bias,
        m15_struct.last_swing_high, m15_struct.last_swing_low,
    )

    if direction == "buy":
        sweep = bool(zone and any(
            c.low < zone.bottom and c.close > zone.bottom for c in m15_candles[-3:]
        ))
        rejection = is_rejection_candle(m15_last, "buy")
    else:
        sweep = bool(zone and any(
            c.high > zone.top and c.close < zone.top for c in m15_candles[-3:]
        ))
        rejection = is_rejection_candle(m15_last, "sell")

    displacement = _is_displacement(m15_candles, direction)
    confirmation: ConfirmationResult = check_entry_confirmation(
        direction=direction,
        h4_bias=h4.bias,
        zone_kind=zone_kind,
        zone_status=zone.status if zone else "invalid",
        price_in_zone=price_in_zone,
        has_sweep=sweep,
        has_rejection=rejection,
        choch_direction=m15_bos_choch.choch,
        has_displacement=displacement,
        confirmation_candle_closed=m15_last.is_closed,
    )

    # --- 7. Risk plan ---
    plan: TradePlan
    if zone and price_in_zone:
        levels = detect_levels(h4.swing_highs, h4.swing_lows)
        if direction == "buy":
            targets = [l.price for l in levels if l.kind == "resistance" and l.price > current_price]
            structure_level = zone.bottom
        else:
            targets = [l.price for l in levels if l.kind == "support" and l.price < current_price]
            structure_level = zone.top
        plan = build_trade_plan(
            direction, entry=current_price, structure_level=structure_level,
            targets=targets, atr_value=atr(m15_candles),
        )
    else:
        plan = TradePlan(direction, current_price, 0, 0, 0, 0, 0, False, "Tidak ada zona aktif.")

    # --- 8. Scoring ---
    score_input = ScoreInput(
        h4_bias_valid=True,
        h4_bos_aligned=h4_bos_choch.bos == direction,
        zone_status=zone.status if zone else "invalid",
        zone_retests=zone.retests if zone else 0,
        order_block_fresh=False,
        fvg_unmitigated=False,
        liquidity_sweep=sweep,
        choch_m15=m15_bos_choch.choch == direction,
        displacement_m15=displacement,
        rr1=plan.rr1 if plan.valid else 0.0,
    )
    score, quality = score_signal(score_input)

    pd = compute_premium_discount(
        current_price, h4.range_high or current_price, h4.range_low or current_price
    )

    # --- 9. Keputusan akhir ---
    if not confirmation.complete:
        signal = "WAIT"
        reasons = confirmation.missing
        invalidation = "Konfirmasi M15 belum lengkap."
    elif not plan.valid:
        signal = "WAIT"
        reasons = [plan.reason]
        invalidation = "Risk/Reward tidak memenuhi syarat."
    else:
        signal = "BUY" if direction == "buy" else "SELL"
        reasons = ["Semua syarat wajib terpenuhi."]
        invalidation = ""

    return MultiTFResult(
        symbol=symbol,
        signal=signal,
        h4_bias=h4.bias,
        h4_structure=h4.structure_label,
        h4_bos=h4_bos_choch.bos,
        h4_choch=h4_bos_choch.choch,
        h1_zone=zone,
        price_in_zone=price_in_zone,
        m15_sweep=sweep,
        m15_rejection=rejection,
        m15_choch=m15_bos_choch.choch,
        m15_displacement=displacement,
        entry=plan.entry if plan.valid else None,
        stop_loss=plan.stop_loss if plan.valid else None,
        tp1=plan.tp1 if plan.valid else None,
        tp2=plan.tp2 if plan.valid else None,
        risk_reward=plan.rr1 if plan.valid else None,
        score=score,
        quality=quality,
        reasons=reasons,
        invalidation=invalidation,
        premium_discount=pd.zone,
    )
