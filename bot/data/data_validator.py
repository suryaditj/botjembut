"""Validasi data candle.

Bot TIDAK boleh menghasilkan sinyal dari data yang gagal, tidak lengkap,
duplikat, atau tidak berurutan. Semua kegagalan harus menghasilkan
keputusan WAIT beserta alasannya.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from bot.models.candle import Candle


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str = ""


def validate_candles(candles: Sequence[Candle], interval: str = "") -> ValidationResult:
    """Validasi deret candle.

    Memeriksa:
      - tidak kosong
      - setiap candle valid (OHLC konsisten)
      - timestamp berurutan naik (tidak boleh ada yang mundur)
      - tidak ada timestamp duplikat
      - jarak antar candle konsisten (tidak ada gap besar)
    """
    if not candles:
        return ValidationResult(False, "Data kosong: tidak ada candle.")

    # 1. Validitas dasar tiap candle
    for i, c in enumerate(candles):
        if not c.is_valid():
            return ValidationResult(
                False, f"Candle #{i} ({c.timestamp}) tidak valid (OHLC tidak konsisten)."
            )

    # 2. Urutan & duplikat
    for i in range(1, len(candles)):
        prev, cur = candles[i - 1], candles[i]
        if cur.timestamp == prev.timestamp:
            return ValidationResult(False, f"Timestamp duplikat ditemukan: {cur.timestamp}.")
        if cur.timestamp < prev.timestamp:
            return ValidationResult(
                False,
                f"Timestamp tidak berurutan: {prev.timestamp} -> {cur.timestamp}.",
            )

    # 3. Konsistensi interval (opsional, hanya jika interval diketahui)
    if interval and len(candles) >= 2:
        expected = _expected_interval(interval)
        if expected is not None:
            for i in range(1, len(candles)):
                delta = candles[i].timestamp - candles[i - 1].timestamp
                # Toleransi: gap lebih dari 2x interval normal dianggap tidak konsisten
                if delta > expected * 2:
                    return ValidationResult(
                        False,
                        f"Gap waktu tidak konsisten pada {candles[i].timestamp} "
                        f"(selisih {delta}).",
                    )

    return ValidationResult(True, "")


def _expected_interval(interval: str) -> timedelta | None:
    mapping = {
        "15min": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }
    return mapping.get(interval)
