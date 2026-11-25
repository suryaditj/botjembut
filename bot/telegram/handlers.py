"""Handler Telegram: menu, aksi, anti-duplicate, dan penanganan error."""
from __future__ import annotations

import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.analysis.multi_tf import analyze_symbol
from bot.analysis.supply_demand import active_zones, detect_zones
from bot.config.settings import settings
from bot.data.candle_fetcher import CandleFetcher, DataFetchError
from bot.telegram import keyboards as kb
from bot.telegram.formatter import format_analysis, format_structure, format_zones

logger = logging.getLogger(__name__)


class SignalStore:
    """Penyimpanan sinyal untuk pencegahan duplikat."""

    def __init__(self) -> None:
        self._last: dict[tuple[int, str], tuple[str, float | None]] = {}

    def is_duplicate(self, chat_id: int, symbol: str, signal: str, entry: float | None) -> bool:
        key = (chat_id, symbol)
        sig = (signal, entry)
        prev = self._last.get(key)
        self._last[key] = sig
        # hanya dianggap duplikat jika sinyal trade yang sama & entry sama
        return prev is not None and prev == sig and signal in ("BUY", "SELL")


class AnalysisService:
    """Menghubungkan pengambilan data dengan mesin analisis."""

    def __init__(self) -> None:
        self.fetcher = CandleFetcher()

    def analyze(self, symbol: str):
        h4 = self.fetcher.get_closed_candles(symbol, "4h")
        h1 = self.fetcher.get_closed_candles(symbol, "1h")
        m15 = self.fetcher.get_closed_candles(symbol, "15min")
        return analyze_symbol(symbol, h4, h1, m15)

    def refresh(self, symbol: str):
        self.fetcher.clear_cache()
        return self.analyze(symbol)

    def zones(self, symbol: str):
        h1 = self.fetcher.get_closed_candles(symbol, "1h")
        zones = detect_zones(h1)
        return active_zones(zones, "demand") + active_zones(zones, "supply")


def _is_authorized(chat_id: int) -> bool:
    if not settings.ALLOWED_CHAT_IDS:
        return True
    return chat_id in settings.ALLOWED_CHAT_IDS


async def _safe_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                     reply_markup: InlineKeyboardMarkup | None = None) -> None:
    """Kirim pesan baru dengan penanganan error Telegram API."""
    try:
        await update.effective_message.reply_text(text, reply_markup=reply_markup)
    except Exception as exc:  # noqa: BLE001
        logger.error("Gagal mengirim pesan Telegram: %s", exc)
        try:
            await update.effective_message.reply_text("⚠️ Terjadi kesalahan saat mengirim pesan.")
        except Exception:  # noqa: BLE001
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Anda tidak diizinkan menggunakan bot ini.")
        return
    await update.effective_message.reply_text(
        "🤖 Selamat datang di Bot Analisis Hybrid SMC + SNR/SND.\n"
        "Pilih market untuk memulai:",
        reply_markup=kb.market_selection_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    chat_id = update.effective_user.id

    if not _is_authorized(chat_id):
        await query.edit_message_text("⛔ Anda tidak diizinkan.")
        return

    service: AnalysisService = context.bot_data.setdefault("analysis_service", AnalysisService())
    store: SignalStore = context.bot_data.setdefault("signal_store", SignalStore())
    current_market: str = context.user_data.get("market", "")

    # --- Pilih market ---
    if data.startswith(kb.CB_MARKET):
        market = data[len(kb.CB_MARKET):]
        context.user_data["market"] = market
        await query.edit_message_text(
            f"Market dipilih: {market.replace('/', '')}\nPilih aksi:",
            reply_markup=kb.action_keyboard(market),
        )
        return

    # --- Aksi ---
    if data == kb.CB_SWITCH_MARKET or data == kb.CB_BACK:
        await query.edit_message_text(
            "Pilih market:",
            reply_markup=kb.market_selection_keyboard(),
        )
        return

    if not current_market:
        await query.edit_message_text("Pilih market terlebih dahulu.", reply_markup=kb.market_selection_keyboard())
        return

    try:
        if data == kb.CB_ANALYZE:
            result = service.analyze(current_market)
            text = format_analysis(result)
            if store.is_duplicate(chat_id, current_market, result.signal, result.entry):
                text += "\n\n⚠️ Sinyal ini sama dengan analisis sebelumnya (anti-duplicate)."
            await _safe_send(update, context, text, kb.action_keyboard(current_market))

        elif data == kb.CB_REFRESH:
            result = service.refresh(current_market)
            text = "🔄 Refresh selesai (data terbaru).\n\n" + format_analysis(result)
            await _safe_send(update, context, text, kb.action_keyboard(current_market))

        elif data == kb.CB_ZONES:
            zones = service.zones(current_market)
            await _safe_send(update, context, format_zones(current_market, zones), kb.action_keyboard(current_market))

        elif data == kb.CB_STRUCTURE:
            result = service.analyze(current_market)
            await _safe_send(update, context, format_structure(result), kb.action_keyboard(current_market))

        else:
            await query.edit_message_text("Aksi tidak dikenal.", reply_markup=kb.action_keyboard(current_market))

    except DataFetchError as exc:
        await _safe_send(
            update, context,
            f"⛔ WAIT — Data gagal diambil/divalidasi.\nAlasan: {exc}",
            kb.action_keyboard(current_market),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error saat memproses aksi %s", data)
        await _safe_send(update, context, f"⚠️ Terjadi kesalahan internal: {exc}")
