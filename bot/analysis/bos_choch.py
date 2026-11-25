"""BOS (Break of Structure) dan CHOCH (Change of Character).

- BOS: penembusan level struktur SEARAH tren (kelanjutan).
- CHOCH: penembusan level struktur MELAWAN tren (sinyal perubahan karakter,
  BUKAN otomatis pembalikan arah — butuh konfirmasi lebih lanjut).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from bot.models.candle import Candle


@dataclass(frozen=True)
class BosChochResult:
    bos: Optional[str]           # "bullish" | "bearish" | None
    choch: Optional[str]         # "bullish" | "bearish" | None
    last_break_level: Optional[float] = None


def detect_bos_choch(
    candles: Sequence[Candle],
    bias: str,
    last_swing_high: Optional[float],
    last_swing_low: Optional[float],
) -> BosChochResult:
    """Deteksi BOS dan CHOCH berdasarkan bias dan swing terakhir."""
    if not candles:
        return BosChochResult(bos=None, choch=None)

    last_close = candles[-1].close

    bos: Optional[str] = None
    choch: Optional[str] = None
    break_level: Optional[float] = None

    if bias == "bullish":
        if last_swing_high is not None and last_close > last_swing_high:
            bos = "bullish"
            break_level = last_swing_high
        if last_swing_low is not None and last_close < last_swing_low:
            choch = "bearish"
            break_level = last_swing_low

    elif bias == "bearish":
        if last_swing_low is not None and last_close < last_swing_low:
            bos = "bearish"
            break_level = last_swing_low
        if last_swing_high is not None and last_close > last_swing_high:
            choch = "bullish"
            break_level = last_swing_high

    # bias neutral -> tidak ada kesimpulan BOS/CHOCH yang valid
    return BosChochResult(bos=bos, choch=choch, last_break_level=break_level)
