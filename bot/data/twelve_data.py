"""Adapter Twelve Data API.

Abstraksi sumber data OHLC. Interface ini yang dipakai oleh seluruh
mesin analisis; jika nanti ingin mengganti penyedia data, cukup buat
adapter baru dengan interface yang sama tanpa menyentuh modul analisis.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import requests

from bot.config.settings import settings
from bot.models.candle import Candle

# Interval yang didukung Twelve Data (dipetakan dari nama internal bot)
INTERVAL_MAP: dict[str, str] = {
    "4h": "4h",
    "1h": "1h",
    "15min": "15min",
}

# Mapping simbol display -> simbol API Twelve Data
# Twelve Data kadang butuh format tanpa slash untuk komoditas/forex tertentu
SYMBOL_MAP: dict[str, str] = {
    "XAU/USD": "XAUUSD",
    "BTC/USD": "BTC/USD",  # crypto biasanya pakai slash
}


class TwelveDataError(Exception):
    """Error umum dari Twelve Data."""


class TwelveDataRateLimitError(TwelveDataError):
    """Rate limit / kuota API tercapai."""


class TwelveDataAuthError(TwelveDataError):
    """API key tidak valid / tidak berhak."""


class TwelveDataAdapter:
    """Adapter untuk endpoint time_series Twelve Data."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = (api_key or settings.TWELVE_DATA_API_KEY).strip()
        if not self.api_key:
            raise TwelveDataError("TWELVE_DATA_API_KEY belum diatur (lihat .env.example)")
        self.base_url = base_url or settings.TWELVE_API_BASE
        self.timeout = timeout if timeout is not None else settings.TWELVE_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.TWELVE_MAX_RETRIES
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_time_series(
        self,
        symbol: str,
        interval: str,
        outputsize: int = 300,
    ) -> list[Candle]:
        """Ambil deret waktu OHLC sebagai list Candle (sudah diurutkan naik)."""
        if interval not in INTERVAL_MAP:
            raise TwelveDataError(f"Interval tidak didukung: {interval}")

        # Konversi simbol ke format API Twelve Data
        api_symbol = SYMBOL_MAP.get(symbol, symbol)

        params = {
            "symbol": api_symbol,
            "interval": INTERVAL_MAP[interval],
            "outputsize": outputsize,
            "apikey": self.api_key,
            "order": "ASC",
        }

        payload = self._request_with_retry(params)
        values = payload.get("values")
        if not isinstance(values, list) or not values:
            raise TwelveDataError(
                f"Tidak ada data OHLC untuk {symbol} {interval} "
                f"(status={payload.get('status')!r})"
            )

        candles: list[Candle] = []
        for row in values:
            ts = self._parse_timestamp(row.get("datetime"))
            if ts is None:
                raise TwelveDataError(f"Timestamp tidak valid pada data {symbol} {interval}")
            try
