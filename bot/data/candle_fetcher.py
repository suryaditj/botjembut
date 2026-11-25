"""Fetcher candle dengan caching dan penanganan candle berjalan.

Prinsip anti-repaint: candle TERAKHIR dari API dianggap masih berjalan
(belum tertutup) dan SELALU dibuang sebelum analisis. Sinyal hanya
dibangun dari candle tertutup.
"""
from __future__ import annotations

import time
from typing import Optional

from bot.config.settings import settings
from bot.data.data_validator import ValidationResult, validate_candles
from bot.data.twelve_data import TwelveDataAdapter
from bot.models.candle import Candle


class DataFetchError(Exception):
    """Gagal mengambil / memvalidasi data."""


class CandleFetcher:
    def __init__(
        self,
        adapter: Optional[TwelveDataAdapter] = None,
        cache_ttl: Optional[int] = None,
    ) -> None:
        self.adapter = adapter or TwelveDataAdapter()
        self.cache_ttl = cache_ttl if cache_ttl is not None else settings.CACHE_TTL_SECONDS
        # key: (symbol, interval) -> (fetched_at, list[Candle])
        self._cache: dict[tuple[str, str], tuple[float, list[Candle]]] = {}

    def get_closed_candles(
        self,
        symbol: str,
        interval: str,
        outputsize: Optional[int] = None,
    ) -> list[Candle]:
        """Ambil candle tertutup yang valid untuk analisis.

        Mengembalikan list candle yang sudah TANPA candle berjalan (terakhir),
        diurutkan naik, dan lolos validasi. Jika validasi gagal, raise
        DataFetchError (pemanggil harus menangani -> WAIT).
        """
        count = outputsize or settings.CANDLE_COUNT.get(interval, 300)

        # 1. Cek cache
        cached = self._cache.get((symbol, interval))
        now = time.monotonic()
        if cached is not None:
            fetched_at, candles = cached
            if now - fetched_at < self.cache_ttl:
                return candles

        # 2. Ambil dari API
        raw = self.adapter.fetch_time_series(symbol, interval, outputsize=count)

        # 3. Validasi data mentah (sebelum membuang candle berjalan)
        result: ValidationResult = validate_candles(raw, interval)
        if not result.valid:
            raise DataFetchError(f"Validasi data gagal ({symbol} {interval}): {result.reason}")

        # 4. Buang candle berjalan (terakhir) -> anti-repaint
        if len(raw) < 2:
            raise DataFetchError(
                f"Data terlalu sedikit untuk analisis ({symbol} {interval}): {len(raw)} candle."
            )
        closed = raw[:-1]

        # 5. Validasi ulang setelah pembuangan (harus tetap konsisten)
        result2 = validate_candles(closed, interval)
        if not result2.valid:
            raise DataFetchError(
                f"Validasi ulang gagal ({symbol} {interval}): {result2.reason}"
            )

        # 6. Simpan cache
        self._cache[(symbol, interval)] = (now, closed)
        return closed

    def clear_cache(self) -> None:
        self._cache.clear()
