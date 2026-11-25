"""Konfigurasi global bot.

Semua nilai sensitif dibaca dari environment variables (via .env).
Jangan pernah hardcode API key / token di source code.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Muat .env dari root project (dua level di atas file ini: bot/config/settings.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


class Settings:
    """Container konfigurasi terpusat."""

    # --- API keys (wajib bila bot dijalankan) ---
    TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    # --- Otorisasi Telegram (opsional) ---
    ALLOWED_CHAT_IDS: set[int] = {
        int(x.strip())
        for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
        if x.strip().lstrip("-").isdigit()
    }

    # --- Market & timeframe ---
    SYMBOLS: tuple[str, ...] = ("XAU/USD", "BTC/USD")
    TIMEFRAMES: tuple[str, ...] = ("4h", "1h", "15min")

    # --- Jumlah candle ---
    CANDLE_COUNT: dict[str, int] = {
        "4h": _get_int("CANDLE_COUNT_H4", 300),
        "1h": _get_int("CANDLE_COUNT_H1", 300),
        "15min": _get_int("CANDLE_COUNT_M15", 300),
    }

    # --- Caching ---
    CACHE_TTL_SECONDS: int = _get_int("CACHE_TTL_SECONDS", 60)

    # --- Twelve Data API ---
    TWELVE_API_BASE: str = "https://api.twelvedata.com"
    TWELVE_TIMEOUT: float = 15.0
    TWELVE_MAX_RETRIES: int = 2

    # --- Parameter analisis ---
    SWING_LEFT_RIGHT: int = 1          # jumlah candle kiri/kanan untuk konfirmasi swing
    MAX_ZONES_PER_SIDE: int = 3        # maksimal zona aktif per arah
    MIN_RISK_REWARD: float = 2.0       # RR minimum 1:2
    SL_BUFFER_ATR: float = 0.5         # buffer SL dalam satuan ATR
    STRONG_SCORE: int = 85
    GOOD_SCORE: int = 75
    WEAK_SCORE: int = 60


settings = Settings()
