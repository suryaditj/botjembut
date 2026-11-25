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

# Hanya simbol berikut yang didukung:
# - Input "XAUUSD" atau "XAU/USD" -> dinormalisasi ke "XAUUSD"
# - Input "BTC/USD" -> dipertahankan sebagai "BTC/USD"
SUPPORTED_SYMBOLS: dict[str, str] = {
    "XAUUSD": "XAUUSD",
    "XAU/USD": "XAUUSD",
    "BTC/USD": "BTC/USD",
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

    @staticmethod
    def _resolve_symbol(symbol: str) -> str:
        cleaned = symbol.strip().strip('"').strip("'").strip().upper()
        if cleaned not in SUPPORTED_SYMBOLS:
            raise TwelveDataError(
                f"Simbol tidak didukung: {symbol!r}. Hanya mendukung XAUUSD dan BTC/USD."
            )
        return SUPPORTED_SYMBOLS[cleaned]

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

        api_symbol = self._resolve_symbol(symbol)

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
            try:
                candle = Candle(
                    timestamp=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                    is_closed=True,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise TwelveDataError(
                    f"Field OHLC tidak lengkap pada {symbol} {interval}: {exc}"
                ) from exc
            if not candle.is_valid():
                raise TwelveDataError(
                    f"Candle tidak valid pada {symbol} {interval} di {ts}"
                )
            candles.append(candle)

        return candles

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _request_with_retry(self, params: dict) -> dict:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._session.get(
                    f"{self.base_url}/time_series",
                    params=params,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                break

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("status") == "error":
                    code = data.get("code")
                    msg = data.get("message") or "Error tidak diketahui dari Twelve Data"
                    if code == 401:
                        raise TwelveDataAuthError(f"API key Twelve Data tidak valid: {msg}")
                    if code == 429:
                        raise TwelveDataRateLimitError(f"Rate limit Twelve Data tercapai: {msg}")
                    raise TwelveDataError(f"Twelve Data error {code}: {msg}")
                return data

            if resp.status_code == 401:
                raise TwelveDataAuthError("API key Twelve Data tidak valid (401)")
            if resp.status_code == 429:
                raise TwelveDataRateLimitError("Rate limit / kuota Twelve Data tercapai (429)")
            if resp.status_code == 403:
                raise TwelveDataAuthError("Akses ditolak Twelve Data (403)")

            try:
                data = resp.json()
            except ValueError:
                data = {}
            msg = data.get("message") or data.get("error") or resp.text[:200]
            last_exc = TwelveDataError(f"Twelve Data HTTP {resp.status_code}: {msg}")
            if attempt < self.max_retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            break

        if isinstance(last_exc, TwelveDataError):
            raise last_exc
        raise TwelveDataError(f"Gagal menghubungi Twelve Data: {last_exc}")

    @staticmethod
    def _parse_timestamp(raw) -> Optional[datetime]:
        if not raw:
            return None
        raw = str(raw).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None
