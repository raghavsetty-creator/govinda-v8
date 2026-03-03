"""
NIFTY AI Trading System — Multi-Timeframe Analysis
====================================================
Fetches and analyzes NIFTY across multiple timeframes.
Higher timeframes set the BIAS. Lower timeframes set the ENTRY.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from knowledge.market_knowledge import MTF_RULES, INDICATOR_KNOWLEDGE
import config

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """
    Fetches NIFTY data across 5 timeframes and generates:
    - Per-timeframe trend analysis
    - Alignment score (0-10)
    - Overall bias recommendation
    - Confluence level rating
    """

    TIMEFRAMES = {
        "1d":  {"label": "Daily",   "period": "6mo",  "weight": 5},
        "1h":  {"label": "Hourly",  "period": "30d",  "weight": 3},
        "15m": {"label": "15-Min",  "period": "10d",  "weight": 2},
        "5m":  {"label": "5-Min",   "period": "5d",   "weight": 1},
    }

    def __init__(self):
        self.tf_data    = {}
        self.tf_signals = {}

    def analyze_all_timeframes(self) -> dict:
        """Fetch and analyze all timeframes. Returns full MTF report."""
        logger.info("Running multi-timeframe analysis...")

        for tf, meta in self.TIMEFRAMES.items():
            try:
                df = self._fetch_tf(tf, meta["period"])
                if df is not None and len(df) > 50:
                    self.tf_data[tf]    = df
                    self.tf_signals[tf] = self._analyze_single_tf(df, tf, meta["label"])
                    logger.info(f"  {meta['label']}: {self.tf_signals[tf]['bias']} | Score={self.tf_signals[tf]['score']}")
            except Exception as e:
                logger.warning(f"  {tf} analysis failed: {e}")

        return self._compile_mtf_report()

    def analyze_from_data(self, df_dict: dict) -> dict:
        """
        Analyze from pre-fetched DataFrames.
        df_dict = {"5m": df_5m, "15m": df_15m, "1h": df_1h, "1d": df_1d}
        """
        for tf, df in df_dict.items():
            if tf in self.TIMEFRAMES and df is not None and len(df) > 20:
                meta = self.TIMEFRAMES[tf]
                self.tf_data[tf]    = df
                self.tf_signals[tf] = self._analyze_single_tf(df, tf, meta["label"])
        return self._compile_mtf_report()

    def _fetch_tf(self, interval: str, period: str) -> pd.DataFrame:
        """Fetch data for a single timeframe."""
        try:
            df = yf.download(config.SYMBOL, period=period, interval=interval, progress=False)
            if df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            return df
        except Exception as e:
            logger.warning(f"Fetch failed for {interval}: {e}")
            return None

    def _analyze_single_tf(self, df: pd.DataFrame, tf: str, label: str) -> dict:
        """Deep analysis of a single timeframe."""
        c = df["close"]; h = df["high"]; l = df["low"]

        # EMAs
        ema9  = c.ewm(span=9,   adjust=False).mean()
        ema21 = c.ewm(span=21,  adjust=False).mean()
        ema50 = c.ewm(span=50,  adjust=False).mean()
        ema200= c.ewm(span=200, adjust=False).mean()

        # ADX
        tr    = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
        dm_p  = (h - h.shift(1)).where((h - h.shift(1)) > (l.shift(1) - l), 0).clip(lower=0)
        dm_m  = (l.shift(1) - l).where((l.shift(1) - l) > (h - h.shift(1)), 0).clip(lower=0)
        atr14 = tr.ewm(alpha=1/14).mean()
        dip   = 100 * dm_p.ewm(alpha=1/14).mean() / (atr14 + 1e-9)
        dim   = 100 * dm_m.ewm(alpha=1/14).mean() / (atr14 + 1e-9)
        dx    = 100 * (dip - dim).abs() / (dip + dim + 1e-9)
        adx   = dx.ewm(alpha=1/14).mean()

        # RSI
        delta   = c.diff()
        avg_g   = delta.where(delta > 0, 0).ewm(alpha=1/14).mean()
        avg_l   = (-delta).where(delta < 0, 0).ewm(alpha=1/14).mean()
        rsi     = 100 - 100 / (1 + avg_g / (avg_l + 1e-9))

        # Latest values
        price   = float(c.iloc[-1])
        ema9_v  = float(ema9.iloc[-1])
        ema21_v = float(ema21.iloc[-1])
        ema50_v = float(ema50.iloc[-1])
        ema200_v= float(ema200.iloc[-1])
        adx_v   = float(adx.iloc[-1])
        dip_v   = float(dip.iloc[-1])
        dim_v   = float(dim.iloc[-1])
        rsi_v   = float(rsi.iloc[-1])

        # Determine bias
        score = 0
        reasons = []

        if price > ema9_v:  score += 1; reasons.append("Price > EMA9")
        if price > ema21_v: score += 1; reasons.append("Price > EMA21")
        if price > ema50_v: score += 1; reasons.append("Price > EMA50")
        if price > ema200_v:score += 2; reasons.append("Price > EMA200 (major bullish)")
        if ema9_v > ema21_v:score += 1; reasons.append("EMA9 > EMA21 (bullish cross)")
        if adx_v > 25:      score += 1; reasons.append(f"ADX={adx_v:.0f} — strong trend")
        if dip_v > dim_v:   score += 1; reasons.append("DI+ > DI- (bullish)")
        if rsi_v > 55:      score += 1; reasons.append(f"RSI={rsi_v:.0f} — bullish momentum")

        # Bearish deductions
        bearish_score = 0
        bear_reasons = []
        if price < ema9_v:   bearish_score += 1; bear_reasons.append("Price < EMA9")
        if price < ema21_v:  bearish_score += 1; bear_reasons.append("Price < EMA21")
        if price < ema50_v:  bearish_score += 1; bear_reasons.append("Price < EMA50")
        if price < ema200_v: bearish_score += 2; bear_reasons.append("Price < EMA200 (major bearish)")
        if dim_v > dip_v:    bearish_score += 1; bear_reasons.append("DI- > DI+ (bearish)")
        if rsi_v < 45:       bearish_score += 1; bear_reasons.append(f"RSI={rsi_v:.0f} — bearish momentum")

        net_score  = score - bearish_score
        bias = "BULLISH" if net_score >= 3 else ("BEARISH" if net_score <= -3 else "NEUTRAL")
        trend_strength = "STRONG" if adx_v > 30 else ("MODERATE" if adx_v > 20 else "WEAK")

        return {
            "timeframe":     tf,
            "label":         label,
            "price":         price,
            "bias":          bias,
            "score":         net_score,
            "trend_strength": trend_strength,
            "adx":           round(adx_v, 1),
            "rsi":           round(rsi_v, 1),
            "di_plus":       round(dip_v, 1),
            "di_minus":      round(dim_v, 1),
            "ema9":          round(ema9_v, 1),
            "ema21":         round(ema21_v, 1),
            "ema50":         round(ema50_v, 1),
            "ema200":        round(ema200_v, 1),
            "above_ema200":  price > ema200_v,
            "bull_reasons":  reasons,
            "bear_reasons":  bear_reasons,
        }

    def _compile_mtf_report(self) -> dict:
        """Compile all timeframe signals into final MTF report."""
        if not self.tf_signals:
            return {"error": "No timeframe data available"}

        # Weighted alignment score
        total_weight     = 0
        weighted_score   = 0
        bullish_tfs      = []
        bearish_tfs      = []
        neutral_tfs      = []

        for tf, sig in self.tf_signals.items():
            weight = self.TIMEFRAMES.get(tf, {}).get("weight", 1)
            weighted_score += sig["score"] * weight
            total_weight   += weight * 10  # normalize

            if sig["bias"] == "BULLISH":   bullish_tfs.append(sig["label"])
            elif sig["bias"] == "BEARISH": bearish_tfs.append(sig["label"])
            else:                          neutral_tfs.append(sig["label"])

        # Confluence score 0-10
        confluence = min(10, max(0, 5 + weighted_score / max(total_weight / 10, 1)))

        # Overall bias
        if len(bullish_tfs) >= 3:
            overall_bias = "STRONG_BULLISH"
        elif len(bearish_tfs) >= 3:
            overall_bias = "STRONG_BEARISH"
        elif len(bullish_tfs) > len(bearish_tfs):
            overall_bias = "MILD_BULLISH"
        elif len(bearish_tfs) > len(bullish_tfs):
            overall_bias = "MILD_BEARISH"
        else:
            overall_bias = "CONFLICTED"

        # Trade recommendation
        recommendation = self._get_recommendation(overall_bias, confluence)

        return {
            "overall_bias":   overall_bias,
            "confluence":     round(confluence, 1),
            "bullish_tfs":    bullish_tfs,
            "bearish_tfs":    bearish_tfs,
            "neutral_tfs":    neutral_tfs,
            "recommendation": recommendation,
            "timeframes":     self.tf_signals,
            "rule_reference": MTF_RULES["confluence_scoring"],
        }

    def _get_recommendation(self, bias: str, confluence: float) -> dict:
        if confluence >= 8:
            if "BULLISH" in bias:
                return {"action": "BUY", "confidence": "HIGH",
                        "note": "All major TFs aligned bullish — high probability long"}
            elif "BEARISH" in bias:
                return {"action": "SELL", "confidence": "HIGH",
                        "note": "All major TFs aligned bearish — high probability short"}
        elif confluence >= 6:
            if "BULLISH" in bias:
                return {"action": "BUY", "confidence": "MODERATE",
                        "note": "Majority TFs bullish — manageable long"}
            elif "BEARISH" in bias:
                return {"action": "SELL", "confidence": "MODERATE",
                        "note": "Majority TFs bearish — manageable short"}
        return {"action": "WAIT", "confidence": "LOW",
                "note": "TFs conflicted — wait for alignment before entering"}

    def get_summary_text(self) -> str:
        """Human-readable MTF summary for AI prompt injection."""
        report = self._compile_mtf_report()
        lines = [
            f"MTF ANALYSIS SUMMARY:",
            f"Overall Bias: {report.get('overall_bias', 'N/A')}",
            f"Confluence Score: {report.get('confluence', 0)}/10",
            f"Bullish TFs: {', '.join(report.get('bullish_tfs', ['None']))}",
            f"Bearish TFs: {', '.join(report.get('bearish_tfs', ['None']))}",
            f"Recommendation: {report.get('recommendation', {}).get('action', 'WAIT')} "
            f"({report.get('recommendation', {}).get('confidence', 'LOW')})",
        ]
        for tf, sig in report.get("timeframes", {}).items():
            lines.append(
                f"  {sig['label']:8s}: {sig['bias']:12s} | ADX={sig['adx']:4.1f} | RSI={sig['rsi']:4.1f}"
            )
        return "\n".join(lines)
