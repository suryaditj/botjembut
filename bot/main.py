"""Entry point bot Telegram.

Jalankan dari /workspace:
    ./venv/bin/python -m bot.main
"""
from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.config.settings import settings
from bot.telegram.handlers import handle_callback, start

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN belum diatur. Salin .env.example ke .env lalu isi token."
        )
    if not settings.TWELVE_DATA_API_KEY:
        raise SystemExit("TWELVE_DATA_API_KEY belum diatur. Periksa .env.")

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logging.info("Bot Telegram dimulai (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
