"""Supply / Demand zone detection.

Zona terbentuk dari BASE candle (konsolidasi / range kecil) yang diikuti
DEPARTURE candle (pergerakan kuat):
  - Departure bullish menembus base -> DEMAND zone.
  - Departure bearish menembus base -> SUPPLY zone.

Status zona:
  - fresh: harga belum kembali menyentuh zona.
  - mitigated: harga kembali ke zona dan bereaksi (retest).
  - invalidated: harga menembus zona (penutupan di luar zona).

Aturan: maksimal 3 zona aktif per arah; zona invalid tidak dipakai.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from bot.config.settings import settings
from bot.models.candle import Candle


@dataclass(frozen=True)
class Zone:
    kind: str            # "demand" | "supply"
    top: float
    bottom: float
    index_start: int
    index_end: int
    status: str          # "fresh" | "mitigated" | "invalidated"
    retests: int = 0


def detect_zones(
    candles: Sequence[Candle],
    base_range_mult: float = 0.6,
) -> list[Zone]:
    """Deteksi zona supply/demand dari deret candle."""
    if len(candles) < 3:
        return []

    avg_range = sum(c.range for c in candles) / len(candles)
    small_threshold = base_range_mult * avg_range if avg_range > 0 else float("inf")

    zones: list[Zone] = []
    n = len(candles)
    i = 0
    while i < n - 1:
        j = i
        while j < n and candles[j].range < small_threshold:
            j += 1
        if j == i:
            i += 1
            continue
        if j >= n:
            break

        base = candles[i:j]
        dep = candles[j]
        base_top = max(c.high for c in base)
        base_bottom = min(c.low for c in base)

        if dep.bullish and dep.close > base_top:
            zones.append(Zone("demand", base_top, base_bottom, i, j - 1, "fresh"))
        elif dep.bearish and dep.close < base_bottom:
            zones.append(Zone("supply", base_top, base_bottom, i, j - 1, "fresh"))

        i = j

    return _update_status(candles, zones)


def _update_status(candles: Sequence[Candle], zones: list[Zone]) -> list[Zone]:
    updated: list[Zone] = []
    for zone in zones:
        status = "fresh"
        retests = 0
        for c in candles[zone.index_end + 2:]:
            if zone.kind == "demand":
                if c.low <= zone.top:  # harga masuk zona
                    retests += 1
                    status = "mitigated" if c.close > zone.top else status
                if c.close < zone.bottom:  # tembus ke bawah -> invalid
                    status = "invalidated"
                    break
            else:
                if c.high >= zone.bottom:
                    retests += 1
                    status = "mitigated" if c.close < zone.bottom else status
                if c.close > zone.top:
                    status = "invalidated"
                    break
        updated.append(
            Zone(zone.kind, zone.top, zone.bottom, zone.index_start, zone.index_end, status, retests)
        )
    return updated


def active_zones(zones: Sequence[Zone], kind: str, limit: int | None = None) -> list[Zone]:
    """Zona aktif (tidak invalid) untuk satu arah, paling baru dulu, dibatasi limit."""
    limit = limit if limit is not None else settings.MAX_ZONES_PER_SIDE
    active = [z for z in zones if z.kind == kind and z.status != "invalidated"]
    active.sort(key=lambda z: z.index_end, reverse=True)
    return active[:limit]
