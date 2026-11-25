"""Format hasil analisis untuk tampilan Telegram (ringkas, nyaman di HP)."""
from __future__ import annotations

from bot.analysis.multi_tf import MultiTFResult
from bot.analysis.supply_demand import Zone


def _fmt_price(value) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}"


def _zone_status_label(status: str) -> str:
    return {
        "fresh": "Fresh",
        "mitigated": "Mitigated (retest)",
        "invalidated": "Invalidated",
    }.get(status, status.title())


def format_analysis(result: MultiTFResult) -> str:
    """Format hasil analisis penuh sesuai spesifikasi."""
    zone: Zone | None = result.h1_zone
    bias_label = result.h4_bias.upper() if result.h4_bias != "neutral" else "NEUTRAL"

    lines = [
        "🤖 HYBRID SMC ANALYSIS",
        f"Market: {result.symbol.replace('/', '')}",
        "Timeframe: H4 + H1 + M15",
        "",
        "MARKET DIRECTION",
        f"H4: {bias_label}",
        "",
        "MARKET STRUCTURE",
        f"BOS: {result.h4_bos.upper() if result.h4_bos else '-'}",
        f"CHOCH: {result.h4_choch.upper() if result.h4_choch else '-'}",
        f"Liquidity: {result.premium_discount.upper() or '-'}",
        "",
        "TRADING ZONE",
        f"H1: {zone.kind.upper() if zone else '-'}",
        f"Zone High: {_fmt_price(zone.top if zone else None)}",
        f"Zone Low: {_fmt_price(zone.bottom if zone else None)}",
        f"Zone Status: {_zone_status_label(zone.status) if zone else '-'}",
        "",
        "ENTRY CONFIRMATION",
        "M15:",
        f"Liquidity Sweep: {'YES' if result.m15_sweep else 'NO'}",
        f"CHOCH: {result.m15_choch.upper() if result.m15_choch else '-'}",
        f"Displacement: {'YES' if result.m15_displacement else 'NO'}",
        "",
        "TRADING SIGNAL",
        f"{result.signal}",
        "",
        f"Entry: {_fmt_price(result.entry)}",
        f"Stop Loss: {_fmt_price(result.stop_loss)}",
        f"TP1: {_fmt_price(result.tp1)}",
        f"TP2: {_fmt_price(result.tp2)}",
        f"Risk/Reward: {f'{result.risk_reward:.2f}' if result.risk_reward else '-'}",
        "",
        f"Signal Quality: {result.quality} ({result.score})" if result.score is not None else "Signal Quality: -",
        f"Reason: {'; '.join(result.reasons) or '-'}",
        f"Invalidation: {result.invalidation or '-'}",
    ]
    return "\n".join(lines)


def format_zones(symbol: str, zones: list[Zone]) -> str:
    """Format daftar zona supply/demand."""
    if not zones:
        return f"📍 Tidak ada zona aktif untuk {symbol.replace('/', '')}."
    lines = [f"📍 ZONA {symbol.replace('/', '').upper()}", ""]
    for z in zones:
        lines.append(f"{z.kind.upper()} [{_zone_status_label(z.status)}]")
        lines.append(f"  High: {_fmt_price(z.top)}")
        lines.append(f"  Low: {_fmt_price(z.bottom)}")
        lines.append(f"  Retest: {z.retests}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_structure(result: MultiTFResult) -> str:
    """Format ringkasan struktur market H4."""
    return (
        f"📈 MARKET STRUCTURE — {result.symbol.replace('/', '')}\n"
        f"H4 Bias: {result.h4_bias.upper()}\n"
        f"Struktur: {result.h4_structure}\n"
        f"BOS: {result.h4_bos.upper() if result.h4_bos else '-'}\n"
        f"CHOCH: {result.h4_choch.upper() if result.h4_choch else '-'}\n"
        f"Premium/Discount: {result.premium_discount.upper()}"
    )
