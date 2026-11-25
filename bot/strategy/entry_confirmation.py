"""Konfirmasi entry M15.

Syarat wajib BUY:
  1. H4 bullish.
  2. Harga berada di zona demand H1 yang valid.
  3. Ada rejection atau liquidity sweep.
  4. CHOCH bullish terkonfirmasi (M15).
  5. Ada displacement bullish.
  6. Candle konfirmasi sudah tertutup.

SELL berlaku sebaliknya. Menyentuh zona saja TIDAK cukup.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bot.models.candle import Candle


@dataclass(frozen=True)
class ConfirmationResult:
    complete: bool
    missing: list[str]
    details: dict


def is_rejection_candle(candle: Candle, direction: str) -> bool:
    """Rejection candle: wick panjang melawan arah entry."""
    if candle.body <= 0:
        return False
    if direction == "buy":
        return candle.lower_wick > candle.body * 1.5
    if direction == "sell":
        return candle.upper_wick > candle.body * 1.5
    return False


def check_entry_confirmation(
    direction: str,                 # "buy" | "sell"
    h4_bias: str,
    zone_kind: str,
    zone_status: str,
    price_in_zone: bool,
    has_sweep: bool,
    has_rejection: bool,
    choch_direction: Optional[str],
    has_displacement: bool,
    confirmation_candle_closed: bool,
) -> ConfirmationResult:
    missing: list[str] = []
    details: dict = {}

    if direction == "buy":
        if h4_bias != "bullish":
            missing.append("H4 tidak bullish")
        if not (zone_kind == "demand" and zone_status != "invalidated" and price_in_zone):
            missing.append("Harga tidak berada di zona demand H1 yang valid")
        if not (has_sweep or has_rejection):
            missing.append("Tidak ada rejection / liquidity sweep")
        if choch_direction != "bullish":
            missing.append("CHOCH bullish M15 belum terkonfirmasi")
        if not has_displacement:
            missing.append("Tidak ada displacement bullish")
        if not confirmation_candle_closed:
            missing.append("Candle konfirmasi belum tertutup")
    elif direction == "sell":
        if h4_bias != "bearish":
            missing.append("H4 tidak bearish")
        if not (zone_kind == "supply" and zone_status != "invalidated" and price_in_zone):
            missing.append("Harga tidak berada di zona supply H1 yang valid")
        if not (has_sweep or has_rejection):
            missing.append("Tidak ada rejection / liquidity sweep")
        if choch_direction != "bearish":
            missing.append("CHOCH bearish M15 belum terkonfirmasi")
        if not has_displacement:
            missing.append("Tidak ada displacement bearish")
        if not confirmation_candle_closed:
            missing.append("Candle konfirmasi belum tertutup")
    else:
        missing.append("Arah tidak valid")

    details = {
        "h4_bias": h4_bias,
        "zone_kind": zone_kind,
        "zone_status": zone_status,
        "price_in_zone": price_in_zone,
        "has_sweep": has_sweep,
        "has_rejection": has_rejection,
        "choch_direction": choch_direction,
        "has_displacement": has_displacement,
        "confirmation_candle_closed": confirmation_candle_closed,
    }

    return ConfirmationResult(complete=len(missing) == 0, missing=missing, details=details)
