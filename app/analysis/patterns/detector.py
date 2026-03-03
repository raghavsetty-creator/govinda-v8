"""
NIFTY AI Trading System — Candlestick & Chart Pattern Detector
==============================================================
Detects all major candlestick and chart patterns from OHLCV data.
Outputs pattern signals as features for the ML model.
"""

import pandas as pd
import numpy as np
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge.market_knowledge import CANDLESTICK_PATTERNS, CHART_PATTERNS

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detects candlestick and chart patterns from OHLCV DataFrame.
    Returns a DataFrame with pattern columns added (0 = not present, 1/−1 = bullish/bearish).
    """

    def detect_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._detect_candlestick_patterns(df)
        df = self._detect_chart_patterns(df)
        df = self._compute_pattern_score(df)
        logger.info(f"Pattern detection complete. {len([c for c in df.columns if c.startswith('pat_')])} pattern columns added.")
        return df

    # ─────────────────────────────────────────────────────────────────────
    # CANDLESTICK PATTERNS
    # ─────────────────────────────────────────────────────────────────────

    def _detect_candlestick_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        o = df["open"]; h = df["high"]; l = df["low"]; c = df["close"]

        body       = (c - o).abs()
        total_rng  = h - l + 1e-9
        upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
        lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l
        body_pct   = body / total_rng
        avg_body   = body.rolling(10).mean()
        is_bull    = c > o
        is_bear    = c < o

        # ── DOJI ──
        df["pat_doji"] = (body < total_rng * 0.1).astype(int)

        # ── GRAVESTONE DOJI ──
        df["pat_gravestone_doji"] = (
            df["pat_doji"] & (upper_wick > total_rng * 0.6) & (lower_wick < total_rng * 0.1)
        ).astype(int) * -1  # bearish

        # ── DRAGONFLY DOJI ──
        df["pat_dragonfly_doji"] = (
            df["pat_doji"] & (lower_wick > total_rng * 0.6) & (upper_wick < total_rng * 0.1)
        ).astype(int)  # bullish

        # ── HAMMER ──
        df["pat_hammer"] = (
            is_bull &
            (lower_wick >= 2 * body) &
            (upper_wick <= 0.3 * body) &
            (body > avg_body * 0.5)
        ).astype(int)

        # ── SHOOTING STAR ──
        df["pat_shooting_star"] = (
            (upper_wick >= 2 * body) &
            (lower_wick <= 0.3 * body) &
            (body > avg_body * 0.5)
        ).astype(int) * -1  # bearish

        # ── INVERTED HAMMER ──
        df["pat_inverted_hammer"] = (
            is_bull &
            (upper_wick >= 2 * body) &
            (lower_wick <= 0.3 * body)
        ).astype(int)

        # ── HANGING MAN (hammer shape after uptrend) ──
        df["pat_hanging_man"] = (
            is_bear &
            (lower_wick >= 2 * body) &
            (upper_wick <= 0.3 * body) &
            (c.shift(1) > c.shift(3))  # after uptrend
        ).astype(int) * -1  # bearish

        # ── BULLISH MARUBOZU ──
        df["pat_marubozu_bull"] = (
            is_bull & (upper_wick < body * 0.05) & (lower_wick < body * 0.05) & (body > avg_body * 1.5)
        ).astype(int)

        # ── BEARISH MARUBOZU ──
        df["pat_marubozu_bear"] = (
            is_bear & (upper_wick < body * 0.05) & (lower_wick < body * 0.05) & (body > avg_body * 1.5)
        ).astype(int) * -1

        # ── SPINNING TOP ──
        df["pat_spinning_top"] = (
            (body_pct < 0.3) & (upper_wick > body * 0.5) & (lower_wick > body * 0.5)
        ).astype(int)

        # ── BULLISH ENGULFING ──
        df["pat_bullish_engulfing"] = (
            is_bull &
            is_bear.shift(1) &
            (o < c.shift(1)) &
            (c > o.shift(1)) &
            (body > body.shift(1))
        ).astype(int)

        # ── BEARISH ENGULFING ──
        df["pat_bearish_engulfing"] = (
            is_bear &
            is_bull.shift(1) &
            (o > c.shift(1)) &
            (c < o.shift(1)) &
            (body > body.shift(1))
        ).astype(int) * -1

        # ── BULLISH HARAMI ──
        df["pat_bullish_harami"] = (
            is_bull &
            is_bear.shift(1) &
            (o > c.shift(1)) &
            (c < o.shift(1)) &
            (body < body.shift(1) * 0.6)
        ).astype(int)

        # ── BEARISH HARAMI ──
        df["pat_bearish_harami"] = (
            is_bear &
            is_bull.shift(1) &
            (o < c.shift(1)) &
            (c > o.shift(1)) &
            (body < body.shift(1) * 0.6)
        ).astype(int) * -1

        # ── PIERCING LINE ──
        df["pat_piercing_line"] = (
            is_bull &
            is_bear.shift(1) &
            (o < l.shift(1)) &
            (c > (o.shift(1) + c.shift(1)) / 2) &
            (c < o.shift(1))
        ).astype(int)

        # ── DARK CLOUD COVER ──
        df["pat_dark_cloud_cover"] = (
            is_bear &
            is_bull.shift(1) &
            (o > h.shift(1)) &
            (c < (o.shift(1) + c.shift(1)) / 2) &
            (c > o.shift(1))
        ).astype(int) * -1

        # ── MORNING STAR ──
        df["pat_morning_star"] = (
            is_bull &
            df["pat_doji"].shift(1).astype(bool) &
            is_bear.shift(2) &
            (c > (o.shift(2) + c.shift(2)) / 2)
        ).astype(int)

        # ── EVENING STAR ──
        df["pat_evening_star"] = (
            is_bear &
            df["pat_doji"].shift(1).astype(bool) &
            is_bull.shift(2) &
            (c < (o.shift(2) + c.shift(2)) / 2)
        ).astype(int) * -1

        # ── THREE WHITE SOLDIERS ──
        df["pat_three_white_soldiers"] = (
            is_bull & is_bull.shift(1) & is_bull.shift(2) &
            (c > c.shift(1)) & (c.shift(1) > c.shift(2)) &
            (body > avg_body) & (body.shift(1) > avg_body) & (body.shift(2) > avg_body)
        ).astype(int)

        # ── THREE BLACK CROWS ──
        df["pat_three_black_crows"] = (
            is_bear & is_bear.shift(1) & is_bear.shift(2) &
            (c < c.shift(1)) & (c.shift(1) < c.shift(2)) &
            (body > avg_body) & (body.shift(1) > avg_body) & (body.shift(2) > avg_body)
        ).astype(int) * -1

        # ── TWEEZER BOTTOM ──
        df["pat_tweezer_bottom"] = (
            ((l - l.shift(1)).abs() < total_rng * 0.02) &
            is_bear.shift(1) & is_bull
        ).astype(int)

        # ── TWEEZER TOP ──
        df["pat_tweezer_top"] = (
            ((h - h.shift(1)).abs() < total_rng * 0.02) &
            is_bull.shift(1) & is_bear
        ).astype(int) * -1

        return df

    # ─────────────────────────────────────────────────────────────────────
    # CHART PATTERNS (rolling window detection)
    # ─────────────────────────────────────────────────────────────────────

    def _detect_chart_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        c = df["close"]; h = df["high"]; l = df["low"]

        # ── BULL FLAG ──
        # Strong up move (pole) followed by small consolidation
        pole_return = c.pct_change(10)
        consolidation_range = (h.rolling(5).max() - l.rolling(5).min()) / c
        df["pat_bull_flag"] = (
            (pole_return.shift(5) > 0.015) &   # strong prior move
            (consolidation_range < 0.008) &      # tight consolidation
            (c > c.rolling(5).mean())            # still above recent avg
        ).astype(int)

        # ── BEAR FLAG ──
        df["pat_bear_flag"] = (
            (pole_return.shift(5) < -0.015) &
            (consolidation_range < 0.008) &
            (c < c.rolling(5).mean())
        ).astype(int) * -1

        # ── DOUBLE TOP (rolling 30 bars) ──
        rolling_high = h.rolling(30).max()
        recent_high  = h.rolling(5).max()
        df["pat_double_top"] = (
            (recent_high >= rolling_high * 0.998) &  # near all-time high in window
            (c < rolling_high * 0.995) &              # but closing below
            (c.diff() < 0)                             # and falling
        ).astype(int) * -1

        # ── DOUBLE BOTTOM ──
        rolling_low  = l.rolling(30).min()
        recent_low   = l.rolling(5).min()
        df["pat_double_bottom"] = (
            (recent_low <= rolling_low * 1.002) &
            (c > rolling_low * 1.005) &
            (c.diff() > 0)
        ).astype(int)

        # ── ASCENDING TRIANGLE ──
        flat_top    = (h.rolling(10).max() - h.rolling(10).min()) / h.rolling(10).mean() < 0.005
        rising_lows = l.rolling(10).apply(lambda x: x[-1] > x[0], raw=True).fillna(0)
        df["pat_ascending_triangle"] = (flat_top & (rising_lows == 1)).astype(int)

        # ── DESCENDING TRIANGLE ──
        flat_bottom  = (l.rolling(10).max() - l.rolling(10).min()) / l.rolling(10).mean() < 0.005
        falling_highs = h.rolling(10).apply(lambda x: x[-1] < x[0], raw=True).fillna(0)
        df["pat_descending_triangle"] = (flat_bottom & (falling_highs == 1)).astype(int) * -1

        # ── VOLATILITY SQUEEZE (Bollinger Band Squeeze — pre-breakout) ──
        if "bb_width" in df.columns:
            df["pat_volatility_squeeze"] = (
                df["bb_width"] < df["bb_width"].rolling(20).min() * 1.1
            ).astype(int)
        else:
            df["pat_volatility_squeeze"] = 0

        return df

    # ─────────────────────────────────────────────────────────────────────
    # COMPOSITE PATTERN SCORE
    # ─────────────────────────────────────────────────────────────────────

    def _compute_pattern_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregates all pattern signals into a composite score.
        Positive = bullish, Negative = bearish, 0 = neutral.
        """
        pattern_cols = [c for c in df.columns if c.startswith("pat_")]
        if not pattern_cols:
            df["pattern_score"] = 0
            df["pattern_direction"] = 0
            return df

        df["pattern_score"]     = df[pattern_cols].sum(axis=1)
        df["pattern_direction"] = np.sign(df["pattern_score"])
        df["pattern_strength"]  = df[pattern_cols].abs().sum(axis=1)

        # How many bullish vs bearish patterns firing simultaneously
        df["bullish_pattern_count"] = (df[pattern_cols] > 0).sum(axis=1)
        df["bearish_pattern_count"] = (df[pattern_cols] < 0).sum(axis=1)

        return df

    def get_active_patterns(self, df: pd.DataFrame, bar_idx: int = -1) -> list:
        """Return list of active patterns at a specific bar."""
        pattern_cols = [c for c in df.columns if c.startswith("pat_")]
        row = df.iloc[bar_idx]
        active = []
        for col in pattern_cols:
            val = row.get(col, 0)
            if val != 0:
                pattern_name = col.replace("pat_", "")
                direction = "🟢 BULLISH" if val > 0 else "🔴 BEARISH"
                knowledge = CANDLESTICK_PATTERNS.get(pattern_name, CHART_PATTERNS.get(pattern_name, {}))
                reliability = knowledge.get("reliability", 0.60)
                active.append({
                    "pattern": pattern_name,
                    "direction": direction,
                    "reliability": reliability,
                    "description": knowledge.get("description", ""),
                    "psychology": knowledge.get("psychology", ""),
                })
        return sorted(active, key=lambda x: x["reliability"], reverse=True)
