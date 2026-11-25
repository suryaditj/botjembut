"""Scoring kualitas sinyal (0-100).

Catatan penting: skor BUKAN probabilitas kemenangan, dan TIDAK bisa
mengalahkan syarat wajib. Skor tinggi tetap tidak menghasilkan sinyal bila
syarat wajib (bias H4, zona valid, konfirmasi M15) tidak terpenuhi.
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.config.settings import settings


@dataclass(frozen=True)
class ScoreInput:
    h4_bias_valid: bool = False
    h4_bos_aligned: bool = False
    zone_status: str = "invalid"      # fresh | mitigated | invalid
    zone_retests: int = 0
    order_block_fresh: bool = False
    fvg_unmitigated: bool = False
    liquidity_sweep: bool = False
    choch_m15: bool = False
    displacement_m15: bool = False
    rr1: float = 0.0


def score_signal(inp: ScoreInput) -> tuple[int, str]:
    """Kembalikan (skor, label kualitas)."""
    total = 0

    if inp.h4_bias_valid:
        total += 10
    if inp.h4_bos_aligned:
        total += 10

    if inp.zone_status == "fresh":
        total += 15
    elif inp.zone_status == "mitigated":
        total += 8

    if inp.order_block_fresh:
        total += 10
    if inp.fvg_unmitigated:
        total += 10
    if inp.liquidity_sweep:
        total += 10
    if inp.choch_m15:
        total += 15
    if inp.displacement_m15:
        total += 10

    if inp.rr1 >= 2.0:
        total += 10
    elif inp.rr1 >= 1.5:
        total += 5

    if total >= settings.STRONG_SCORE:
        label = "Sangat kuat"
    elif total >= settings.GOOD_SCORE:
        label = "Kuat"
    elif total >= settings.WEAK_SCORE:
        label = "Lemah"
    else:
        label = "Tidak layak"

    return total, label
