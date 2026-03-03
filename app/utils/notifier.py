"""
GOVINDA Notifier — Telegram alerts for signals, errors, daily summary.
All notifications are fire-and-forget (non-blocking).
"""
import logging, os, threading
import requests

logger = logging.getLogger(__name__)


def _send_async(token: str, chat_id: str, text: str):
    """Send Telegram message in background thread so it never blocks trading."""
    def _do():
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id, "text": text, "parse_mode": "Markdown"
            }, timeout=8)
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
    threading.Thread(target=_do, daemon=True).start()


def _credentials():
    return os.getenv("TELEGRAM_BOT_TOKEN",""), os.getenv("TELEGRAM_CHAT_ID","")


def send_signal(signal: dict):
    token, chat_id = _credentials()
    if not token or not chat_id:
        return
    mode      = signal.get("system_mode","?")
    sig       = signal.get("signal","?")
    conf      = signal.get("confidence", 0)
    entry     = signal.get("entry_day","?")
    expiry    = signal.get("expiry_date","?")
    dte       = signal.get("days_to_expiry","?")
    opts      = signal.get("options_suggestion","N/A")
    tgt       = signal.get("target","N/A")
    sl        = signal.get("stop_loss","N/A")
    size_mult = signal.get("size_multiplier", 1)
    lots      = signal.get("recommended_lots", 1)
    cost      = signal.get("trade_cost", "N/A")
    can_trade = "✅ TRADE" if signal.get("can_trade") else "⏸ ANALYSIS ONLY"

    text = (
        f"🏦 *GOVINDA SIGNAL* `[{mode}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Signal     : *{sig}* ({conf:.0%} conf)\n"
        f"Entry      : {entry}\n"
        f"Expiry     : {expiry} `({dte}d)`\n"
        f"Options    : `{opts}`\n"
        f"Target     : {tgt}  |  SL: {sl}\n"
        f"Size       : {lots} lot(s) × 65 units = ₹{cost}\n"
        f"Action     : {can_trade}\n"
    )
    if signal.get("expiry_shifted"):
        text += "⚠️ _Expiry date shifted due to NSE holiday_\n"
    if signal.get("is_0dte"):
        text += "🟠 *0DTE TRADE — exit ALL positions by 2:30 PM!*\n"
    if size_mult < 1:
        text += f"📉 _Position size reduced to {size_mult:.0%} — mode: {mode}_\n"
    _send_async(token, chat_id, text)


def send_error(msg: str):
    token, chat_id = _credentials()
    if token and chat_id:
        _send_async(token, chat_id, f"🚨 *GOVINDA ERROR*\n```\n{msg[:500]}\n```")


def send_startup(mode: str, entry: str, expiry: str, version: str = "v8"):
    token, chat_id = _credentials()
    if token and chat_id:
        _send_async(token, chat_id,
            f"🟢 *GOVINDA {version} STARTED*\n"
            f"Mode   : `{mode}`\n"
            f"Entry  : {entry}\n"
            f"Expiry : {expiry}"
        )


def send_halt(reason: str):
    token, chat_id = _credentials()
    if token and chat_id:
        _send_async(token, chat_id,
            f"⛔ *GOVINDA TRADING HALTED*\n_{reason}_"
        )


def send_daily_summary(signals: list, pnl_estimate: float = 0):
    token, chat_id = _credentials()
    if not token or not chat_id:
        return
    n    = len(signals)
    wins = sum(1 for s in signals if s.get("outcome") == "WIN")
    text = (
        f"📊 *GOVINDA DAILY SUMMARY*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Signals    : {n}\n"
        f"Wins/Total : {wins}/{n} ({wins/n:.0%})\n" if n else
        f"Signals    : 0 (no trades today)\n"
    )
    if pnl_estimate:
        text += f"Est. P&L   : ₹{pnl_estimate:,.0f}\n"
    _send_async(token, chat_id, text)
