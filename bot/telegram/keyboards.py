"""Inline keyboard Telegram."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Callback data constants
CB_MARKET = "market:"
CB_ANALYZE = "action:analyze"
CB_REFRESH = "action:refresh"
CB_ZONES = "action:zones"
CB_STRUCTURE = "action:structure"
CB_SWITCH_MARKET = "action:switch_market"
CB_BACK = "action:back"


def market_selection_keyboard() -> InlineKeyboardMarkup:
    """Menu awal: Pilih Market."""
    keyboard = [
        [InlineKeyboardButton("XAUUSD", callback_data=CB_MARKET + "XAU/USD")],
        [InlineKeyboardButton("BTCUSD", callback_data=CB_MARKET + "BTC/USD")],
    ]
    return InlineKeyboardMarkup(keyboard)


def action_keyboard(market: str) -> InlineKeyboardMarkup:
    """Menu aksi untuk satu market."""
    keyboard = [
        [InlineKeyboardButton("📊 Analisis Market", callback_data=CB_ANALYZE)],
        [InlineKeyboardButton("🔄 Refresh Analisis", callback_data=CB_REFRESH)],
        [InlineKeyboardButton("📍 Zona Supply/Demand", callback_data=CB_ZONES)],
        [InlineKeyboardButton("📈 Market Structure", callback_data=CB_STRUCTURE)],
        [InlineKeyboardButton("🔁 Ganti Market", callback_data=CB_SWITCH_MARKET)],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data=CB_BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)
