"""Jalankan analisis sekali jalan dan kirim hasilnya ke Telegram.

Dipakai untuk GitHub Actions / cron (one-shot), bukan polling.
Contoh:
    python -m bot.run_analysis --symbol "XAU/USD"
    python -m bot.run_analysis --symbol "BTC/USD" --chat-id 123456789
"""
from __future__ import annotations

import argparse
import logging

import requests

from bot.config.settings import settings
from bot.data.candle_fetcher import DataFetchError
from bot.telegram.formatter import format_analysis
from bot.telegram.handlers import AnalysisService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


def send_telegram(token: str, chat_id: int, text: str) -> None:
    """Kirim pesan via Telegram Bot API (tanpa library polling)."""
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
    resp.raise_for_status()


def _resolve_chat_id(arg_chat_id: int | None) -> int | None:
    if arg_chat_id is not None:
        return arg_chat_id
    if settings.ALLOWED_CHAT_IDS:
        return next(iter(settings.ALLOWED_CHAT_IDS))
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisis one-shot SMC + SNR/SND.")
    parser.add_argument("--symbol", default="XAU/USD", help="Simbol (contoh: XAU/USD, BTC/USD)")
    parser.add_argument("--chat-id", type=int, default=None, help="Chat ID Telegram tujuan (opsional)")
    args = parser.parse_args()

    if not settings.TWELVE_DATA_API_KEY:
        raise SystemExit("TWELVE_DATA_API_KEY belum diatur (cek .env / secrets).")
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diatur (cek .env / secrets).")

    chat_id = _resolve_chat_id(args.chat_id)
    if chat_id is None:
        raise SystemExit("Tidak ada chat_id tujuan. Set ALLOWED_CHAT_IDS atau --chat-id.")

    service = AnalysisService()
    try:
        result = service.analyze(args.symbol)
    except DataFetchError as exc:
        logger.warning("Data gagal diambil: %s", exc)
        send_telegram(settings.TELEGRAM_BOT_TOKEN, chat_id, f"⛔ WAIT — Data gagal diambil/divalidasi.\nAlasan: {exc}")
        return

    text = format_analysis(result)
    send_telegram(settings.TELEGRAM_BOT_TOKEN, chat_id, text)
    logger.info("Analisis %s terkirim ke chat %s (sinyal: %s)", args.symbol, chat_id, result.signal)


if __name__ == "__main__":
    main()
