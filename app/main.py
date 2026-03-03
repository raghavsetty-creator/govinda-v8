from dotenv import load_dotenv; load_dotenv("/opt/govinda/.env")
"""
GOVINDA NIFTY AI Trading System v8 — Orchestrator
==================================================
Full pipeline: Holiday Gate → ML → Patterns → MTF → News → Multi-AI → Signal
Includes: lot sizing, Telegram alerts, Azure blob upload, smart scheduling
"""
import sys, os, time, logging, schedule
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import config
from data.fetcher           import DataFetcher
from data.features          import FeatureEngineer
from models.signal_generator import SelfLearningSignalGenerator
from backtest.backtester    import Backtester
from analysis.patterns.detector import PatternDetector
from analysis.mtf.analyzer  import MultiTimeframeAnalyzer
from analysis.news.sentiment import NewsSentimentAnalyzer
from ai_brain.multi_ai      import AIBrain
from utils.holiday_checker  import should_system_run, trade_calendar_summary
from utils.lot_sizes        import position_size_from_risk, calc_trade_value
from utils.notifier         import send_signal, send_error, send_startup, send_halt, send_daily_summary

os.makedirs(config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{config.LOG_DIR}/govinda_v8.log"),
    ]
)
logger = logging.getLogger(__name__)

# ── Mode metadata ─────────────────────────────────────────────────────────────
MODE_EMOJI = {"OFFLINE":"🔴","NORMAL":"🟢","PRE_EXPIRY":"🟡","EXPIRY_DAY":"🟠"}
MODE_SIZE  = {"OFFLINE":0.0, "NORMAL":1.0, "PRE_EXPIRY":0.5, "EXPIRY_DAY":0.25}


class GOVINDA:
    """
    GOVINDA v8 — Complete pipeline:
    1. Holiday gate  → mode / can_trade / expiry
    2. DataFetcher   → OHLCV
    3. Features      → 30+ indicators
    4. PatternDetect → 25+ patterns
    5. SelfLearnML   → LightGBM + XGBoost signal
    6. MTF           → 4-timeframe confluence
    7. News          → RSS sentiment
    8. AIBrain       → Claude + GPT-4 + Gemini consensus
    9. LotSizing     → position_size_from_risk() with correct 65 lot size
    10.Notify        → Telegram
    """

    def __init__(self):
        logger.info("=" * 70)
        logger.info("GOVINDA NIFTY AI v8 — STARTING")
        logger.info("=" * 70)

        # ── Holiday gate — first thing every time ────────────────────────────
        self.run_check = should_system_run()
        self.cal       = trade_calendar_summary()
        self.mode      = self.run_check["mode"]

        logger.info(f"📅 Mode      : {MODE_EMOJI[self.mode]} {self.mode}")
        logger.info(f"   Reason    : {self.run_check['reason']}")
        logger.info(f"   Entry     : {self.cal['entry_day']}")
        logger.info(f"   Expiry    : {self.cal['expiry_date']} ({self.cal['days_to_expiry']}d)")
        logger.info(f"   Lot Size  : {config.NIFTY_LOT_SIZE} units (NSE Jan 2026)")
        logger.info(f"   Capital   : ₹{config.TRADING_CAPITAL:,.0f}")
        logger.info(f"   Max Risk  : {config.RISK_PER_TRADE_PCT:.0%} per trade")

        if self.cal.get("expiry_shifted"):
            logger.warning(f"   ⚠️  Expiry shifted from {self.cal['natural_expiry']} (holiday)")
        for h in self.cal.get("week_holidays", []):
            if h["is_weekday_closure"]:
                logger.warning(f"   🔴 Holiday this week: {h['name']} on {h['day']}")

        # ── Modules ──────────────────────────────────────────────────────────
        self.fetcher    = DataFetcher()
        self.engineer   = FeatureEngineer()
        self.patterns   = PatternDetector()
        self.model      = SelfLearningSignalGenerator()
        self.mtf        = MultiTimeframeAnalyzer()
        self.news       = NewsSentimentAnalyzer()
        self.ai_brain   = AIBrain()
        self.backtester = Backtester()

        self.df_raw      = None
        self.df_featured = None
        self.signals_today = []
        self.consecutive_losses = 0
        self.daily_loss_rs  = 0.0

        ai_status = self.ai_brain.get_status()
        logger.info(
            f"   AI Active : Claude={'✅' if ai_status['claude'] else '❌'} | "
            f"GPT4={'✅' if ai_status['gpt4'] else '❌'} | "
            f"Gemini={'✅' if ai_status['gemini'] else '❌'}"
        )

        send_startup(self.mode, self.cal["entry_day"], self.cal["expiry_date"])

    def initialize(self) -> bool:
        """Train ML model on historical data. Always runs regardless of mode."""
        logger.info("▶ Initializing ML pipeline...")
        import time as _time
        for _attempt in range(390):
            self.df_raw = self.fetcher.fetch_historical()
            if not self.df_raw.empty:
                break
            logger.warning(f"Data fetch returned 0 candles (attempt {_attempt+1}/5) — retrying in 60s...")
            _time.sleep(60)
        if self.df_raw.empty:
            logger.error("Data fetch failed after 5 attempts")
            send_error("GOVINDA: Historical data fetch failed at startup")
            return False






        self.df_featured = self.engineer.compute_all(self.df_raw)
        self.df_featured = self.patterns.detect_all(self.df_featured)
        df_labeled       = self.engineer.create_labels(self.df_featured)
        metrics = self.model.train(df_labeled)
        if not metrics:
            logger.error("Model training failed")
            send_error("GOVINDA: Model training failed at startup")
            return False

        logger.info(
            f"   Model     : CV={metrics.get('cv_accuracy',0):.3f} | "
            f"BUY precision={metrics.get('precision_buy',0):.3f}"
        )
        df_signals = self.model.generate_signals_batch(self.df_featured)
        results    = self.backtester.run(df_signals)
        if "error" not in results:
            logger.info(
                f"   Backtest  : {results['total_trades']} trades | "
                f"Win={results['win_rate']}% | Sharpe={results['sharpe_ratio']}"
            )
        logger.info("✅ GOVINDA ready")
        return True

    def _check_risk_limits(self) -> tuple[bool, str]:
        """Gate check before each signal — enforce daily loss and loss-streak limits."""
        if self.consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
            return False, f"Consecutive losses: {self.consecutive_losses} ≥ {config.MAX_CONSECUTIVE_LOSSES}"
        daily_loss_pct = self.daily_loss_rs / config.TRADING_CAPITAL
        if daily_loss_pct >= config.MAX_DAILY_LOSS_PCT:
            return False, f"Daily loss {daily_loss_pct:.1%} ≥ {config.MAX_DAILY_LOSS_PCT:.0%} limit"
        if len(self.signals_today) >= config.MAX_DAILY_SIGNALS:
            return False, f"Max daily signals {config.MAX_DAILY_SIGNALS} reached"
        return True, "OK"

    def _calc_lot_sizing(self, signal: dict) -> dict:
        """
        Calculate recommended lot count using correct Jan 2026 lot size (65).
        Respects mode-based size multiplier.
        """
        # Parse premiums from signal
        entry_prem = 110.0  # fallback
        sl_prem    = 40.0

        opts = signal.get("options_suggestion", "")
        tgt  = signal.get("target", "")
        sl   = signal.get("stop_loss", "")

        # Try to extract numeric premium from suggestions if available
        try:
            if sl and "₹" in str(sl):
                sl_prem = float(str(sl).replace("₹","").replace(",","").strip())
            elif sl:
                sl_prem = float(str(sl))
        except:
            pass

        ps = position_size_from_risk(
            symbol          = "NIFTY",
            premium         = entry_prem,
            stop_loss_premium = sl_prem,
            capital         = config.TRADING_CAPITAL,
            risk_pct        = config.RISK_PER_TRADE_PCT,
        )

        # Apply mode multiplier — EXPIRY_DAY = 0.25x, PRE_EXPIRY = 0.5x
        mode_mult = MODE_SIZE.get(signal.get("system_mode","NORMAL"), 1.0)
        adjusted_lots = max(1, int(ps["recommended_lots"] * mode_mult)) if mode_mult > 0 else 0

        tv = calc_trade_value("NIFTY", entry_prem, adjusted_lots)

        return {
            "lot_size":         config.NIFTY_LOT_SIZE,  # 65
            "recommended_lots": ps["recommended_lots"],
            "adjusted_lots":    adjusted_lots,
            "mode_multiplier":  mode_mult,
            "total_qty":        adjusted_lots * config.NIFTY_LOT_SIZE,
            "trade_cost":       tv["total_cost"],
            "risk_per_lot":     ps["risk_per_lot"],
            "max_risk_rs":      round(adjusted_lots * ps["risk_per_lot"], 0),
        }

    def get_signal(self) -> dict:
        """Full pipeline — one complete signal generation cycle."""

        # ── Re-check calendar each call ──────────────────────────────────────
        run_check = should_system_run()
        mode      = run_check["mode"]
        cal       = trade_calendar_summary()

        # ── Risk limit gate ───────────────────────────────────────────────────
        ok, reason = self._check_risk_limits()
        if not ok:
            logger.warning(f"⛔ Trading halted: {reason}")
            send_halt(reason)
            return {"signal":"HALT","reason":reason,"can_trade":False}

        logger.info(f"{MODE_EMOJI[mode]} [{mode}] Generating signal...")

        # ── 1. Data ───────────────────────────────────────────────────────────
        df = self.fetcher.fetch_latest_candles(n=300)
        if df is None or df.empty:
            return {}

        # ── 2–3. Features + patterns ──────────────────────────────────────────
        df = self.engineer.compute_all(df)
        df = self.patterns.detect_all(df)

        # ── 4. ML signal ──────────────────────────────────────────────────────
        ml_signal       = self.model.generate_signal(df)
        active_patterns = self.patterns.get_active_patterns(df)

        # ── 5. MTF ────────────────────────────────────────────────────────────
        try:
            mtf_report = self.mtf.analyze_all_timeframes()
        except Exception as e:
            logger.warning(f"MTF failed: {e}")
            mtf_report = {"overall_bias":"UNKNOWN","confluence":5}

        # ── 6. News ───────────────────────────────────────────────────────────
        try:
            news = self.news.get_market_sentiment()
        except Exception as e:
            logger.warning(f"News failed: {e}")
            news = {"overall_sentiment":"NEUTRAL","sentiment_score":0}

        # ── 7. AI consensus ───────────────────────────────────────────────────
        final = self.ai_brain.get_consensus_signal(
            ml_signal=ml_signal, mtf_report=mtf_report,
            news_sentiment=news, patterns=active_patterns,
        )

        # ── 8. Lot sizing (correct 65 lot size) ───────────────────────────────
        sizing = self._calc_lot_sizing({**final, "system_mode": mode})

        # ── 9. Enrich with all context ────────────────────────────────────────
        final.update({
            # Calendar
            "system_mode":      mode,
            "can_trade":        run_check["should_run"],
            "size_multiplier":  MODE_SIZE[mode],
            "entry_day":        cal["entry_day"],
            "expiry_date":      cal["expiry_date"],
            "days_to_expiry":   cal["days_to_expiry"],
            "expiry_shifted":   cal.get("expiry_shifted", False),
            "natural_expiry":   cal.get("natural_expiry",""),
            "is_0dte":          cal.get("is_0dte", False),
            "week_holidays":    cal.get("week_holidays", []),
            # Lot sizing (Jan 2026 correct sizes)
            "lot_size":         sizing["lot_size"],        # 65
            "recommended_lots": sizing["recommended_lots"],
            "adjusted_lots":    sizing["adjusted_lots"],
            "total_qty":        sizing["total_qty"],
            "trade_cost":       sizing["trade_cost"],
            "max_risk_rs":      sizing["max_risk_rs"],
            # Analysis context
            "market_status":    self.fetcher.get_market_status(),
            "patterns_active":  active_patterns,
            "mtf_report":       mtf_report,
            "news_sentiment":   news,
            "ml_signal":        ml_signal,
        })

        # ── 10. Mode-specific overrides ───────────────────────────────────────
        if mode == "EXPIRY_DAY":
            final["options_suggestion"] = (
                "0DTE: ATM options only | Exit ALL by 2:30 PM | No overnight"
            )
        elif mode == "PRE_EXPIRY":
            risk_note = " | ⚠️ PRE-EXPIRY: theta accelerating, 50% size"
            final["key_risk"] = (final.get("key_risk") or "") + risk_note
        elif mode == "OFFLINE":
            final["action_recommended"] = False
            final["key_risk"] = "Market closed — analysis only, no live orders"

        self.signals_today.append(final)
        self._log_signal(final)

        # ── 11. Notify ────────────────────────────────────────────────────────
        if config.NOTIFY_ON_SIGNAL and final.get("action_recommended"):
            send_signal(final)

        return final

    def _log_signal(self, s: dict):
        mode = s.get("system_mode","?")
        e    = MODE_EMOJI.get(mode,"⚪")
        logger.info("")
        logger.info("=" * 70)
        logger.info(
            f"{e} [{mode}] {s['signal']} | Conf: {s['confidence']:.1%} | "
            f"Agreement: {s.get('agreement','N/A')}"
        )
        logger.info(
            f"   Calendar: Entry {s.get('entry_day','?')} | "
            f"Expiry {s.get('expiry_date','?')} ({s.get('days_to_expiry','?')}d)"
        )
        if s.get("expiry_shifted"):
            logger.warning(f"   ⚠️  Expiry shifted from {s.get('natural_expiry','')}")
        logger.info(
            f"   Lot Size: {s.get('lot_size',65)} | "
            f"Lots: {s.get('adjusted_lots',1)} | "
            f"Qty: {s.get('total_qty',65)} units | "
            f"Cost: ₹{s.get('trade_cost',0):,} | "
            f"Max Risk: ₹{s.get('max_risk_rs',0):,}"
        )
        logger.info(
            f"   MTF: {s.get('mtf_report',{}).get('overall_bias','?')} / "
            f"Confluence {s.get('mtf_report',{}).get('confluence',0)}/10"
        )
        if s.get("options_suggestion") and s["options_suggestion"] != "N/A":
            logger.info(f"   Options : {s['options_suggestion']}")
        if s.get("target") and s["target"] != "N/A":
            logger.info(f"   Target  : {s['target']} | SL: {s.get('stop_loss','?')}")
        logger.info(
            f"   ACTION  : {'✅ TRADE' if s.get('action_recommended') and s.get('can_trade') else '⏸ WAIT'}"
        )
        logger.info("=" * 70)

    def eod_summary(self):
        """Send end-of-day Telegram summary."""
        send_daily_summary(self.signals_today)
        self.signals_today = []
        self.daily_loss_rs = 0.0
        self.consecutive_losses = 0
        logger.info("📊 EOD summary sent, counters reset")

    def get_report(self) -> dict:
        return {
            "last_signal":    self.signals_today[-1] if self.signals_today else {},
            "model_metrics":  self.model.get_performance_summary(),
            "ai_status":      self.ai_brain.get_status(),
            "mode":           self.mode,
            "calendar":       self.cal,
            "signals_today":  len(self.signals_today),
        }


# ── Smart scheduler ────────────────────────────────────────────────────────────

def build_schedule(g: GOVINDA):
    mode = g.mode
    if mode == "OFFLINE":
        schedule.every().day.at("08:00").do(g.initialize)
        schedule.every().day.at("08:30").do(g.get_signal)
        logger.info("📅 OFFLINE: prep 08:00, analysis 08:30")
    elif mode in ("NORMAL","PRE_EXPIRY"):
        for t in ["08:45","09:20","11:00","13:30","15:00"]:
            schedule.every().day.at(t).do(g.get_signal)
        schedule.every().day.at("15:35").do(g.eod_summary)
        logger.info("📅 LIVE: 5 signal windows + EOD summary")
        if mode == "PRE_EXPIRY":
            logger.warning("⚠️ PRE_EXPIRY: sizing at 50%")
    elif mode == "EXPIRY_DAY":
        for t in ["08:45","09:20","10:30","11:30"]:
            schedule.every().day.at(t).do(g.get_signal)
        schedule.every().day.at("14:00").do(_expiry_exit_reminder)
        schedule.every().day.at("15:35").do(g.eod_summary)
        logger.info("📅 EXPIRY_DAY: 4 windows + 2PM hard-exit reminder")


def _expiry_exit_reminder():
    msg = "🟠 EXPIRY DAY — 2:00 PM — CLOSE ALL OPEN POSITIONS BY 2:30 PM"
    logger.warning(msg)
    from utils.notifier import send_halt
    send_halt(msg)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║       GOVINDA NIFTY AI TRADING SYSTEM v8                            ║
║       ML + Patterns + MTF + News + Claude/GPT/Gemini                ║
║       Holiday Gate | Correct Lot Sizes | Azure Ready                ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    g = GOVINDA()
    # Skip initialization on holidays — just run scheduler
    if g.mode == "OFFLINE":
        logger.info("📅 OFFLINE mode — holiday/weekend. Skipping initialization, running scheduler only.")
        build_schedule(g)
        while True:
            schedule.run_pending()
            import time; time.sleep(30)
        return
    if not g.initialize():
        print("❌ Initialization failed.")
        return

    sig = g.get_signal()
    if sig:
        mode = sig.get("system_mode","?")
        e    = MODE_EMOJI.get(mode,"⚪")
        print(f"""
{e}  SIGNAL       : {sig.get('signal','?')}
    Mode         : {mode}
    Confidence   : {sig.get('confidence',0):.1%}
    Entry        : {sig.get('entry_day','?')}
    Expiry       : {sig.get('expiry_date','?')} ({sig.get('days_to_expiry','?')}d)
    {'⚠️  Expiry shifted (holiday correction applied)' if sig.get('expiry_shifted') else '✅ Expiry date verified'}

    ── POSITION SIZING (NSE Jan 2026 lot size = 65) ──
    Lot Size     : {sig.get('lot_size',65)} units
    Lots         : {sig.get('adjusted_lots',1)} lot(s)
    Total Qty    : {sig.get('total_qty',65)} units
    Trade Cost   : ₹{sig.get('trade_cost',0):,}
    Max Risk     : ₹{sig.get('max_risk_rs',0):,}

    ── TRADE ──────────────────────────────────────────
    Options      : {sig.get('options_suggestion','N/A')}
    Target       : {sig.get('target','N/A')}
    Stop Loss    : {sig.get('stop_loss','N/A')}
    Key Risk     : {sig.get('key_risk','N/A')}

    ══════════════════════════════════════════════════
    ACTION : {'✅ TRADE IT' if sig.get('action_recommended') and sig.get('can_trade') else '⏸ ANALYSIS ONLY'}
    ══════════════════════════════════════════════════
        """)

    build_schedule(g)
    print("\n📡 Scheduler running. Ctrl+C to stop.\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n⛔ GOVINDA stopped.")
        g.eod_summary()


if __name__ == "__main__":
    main()
