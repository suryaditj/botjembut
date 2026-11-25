"""Premium / Discount zone.

Berdasarkan range antara swing low dan swing high terakhir:
  - Harga di atas titik tengah (50%) -> PREMIUM.
  - Harga di bawah titik tengah -> DISCOUNT.
Digunakan untuk menilai kualitas entry (beli di discount, jual di premium).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PremiumDiscountResult:
    zone: str          # "premium" | "discount" | "neutral"
    position: float    # 0.0 (di low) s.d. 1.0 (di high)
    midpoint: float


def compute_premium_discount(
    price: float,
    range_high: float,
    range_low: float,
) -> PremiumDiscountResult:
    if range_high <= range_low:
        return PremiumDiscountResult("neutral", 0.5, price)

    midpoint = (range_high + range_low) / 2.0
    span = range_high - range_low
    position = (price - range_low) / span
    position = max(0.0, min(1.0, position))

    if position > 0.5:
        zone = "premium"
    elif position < 0.5:
        zone = "discount"
    else:
        zone = "neutral"

    return PremiumDiscountResult(zone, position, midpoint)
