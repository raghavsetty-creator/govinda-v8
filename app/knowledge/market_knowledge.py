"""
NIFTY AI Trading System — Complete Market Knowledge Base
=========================================================
The "brain" of the system. Contains encoded knowledge of:
  1. All Candlestick Patterns (single, double, triple)
  2. All Chart Patterns (continuation + reversal)
  3. Multi-Timeframe Analysis rules
  4. Open Interest interpretation rules
  5. Technical Indicators (meaning + signals)
  6. Trader Psychology patterns
  7. News impact classification
  8. Market structure rules (Dow Theory, Wyckoff, SMC)
  9. Options-specific knowledge
  10. NIFTY-specific behavioral patterns

This module is QUERIED by the AI brain to generate reasoning.
"""

# ═══════════════════════════════════════════════════════════════════════════
# 1. CANDLESTICK PATTERNS — Complete Encyclopedia
# ═══════════════════════════════════════════════════════════════════════════

CANDLESTICK_PATTERNS = {

    # ── SINGLE CANDLE PATTERNS ──────────────────────────────────────────────

    "doji": {
        "type": "single", "signal": "reversal", "reliability": 0.55,
        "description": "Open ≈ Close. Market indecision. More powerful at extremes.",
        "bullish_context": "After downtrend = potential reversal up",
        "bearish_context": "After uptrend = potential reversal down",
        "confirmation_needed": True,
        "variants": ["standard_doji", "long_legged_doji", "gravestone_doji", "dragonfly_doji"],
    },

    "gravestone_doji": {
        "type": "single", "signal": "bearish_reversal", "reliability": 0.65,
        "description": "Long upper wick, no lower wick, open=close at bottom. Bulls tried, bears won.",
        "best_context": "At resistance levels, after strong uptrend",
        "confirmation_needed": True,
    },

    "dragonfly_doji": {
        "type": "single", "signal": "bullish_reversal", "reliability": 0.65,
        "description": "Long lower wick, no upper wick, open=close at top. Bears tried, bulls won.",
        "best_context": "At support levels, after strong downtrend",
        "confirmation_needed": True,
    },

    "hammer": {
        "type": "single", "signal": "bullish_reversal", "reliability": 0.70,
        "description": "Small body at top, long lower wick (2x+ body), little/no upper wick.",
        "condition": "Must appear after downtrend",
        "psychology": "Bears pushed price down hard but bulls bought the dip aggressively",
        "confirmation_needed": True,
        "volume_confirmation": "Higher volume strengthens signal significantly",
    },

    "inverted_hammer": {
        "type": "single", "signal": "bullish_reversal", "reliability": 0.60,
        "description": "Small body at bottom, long upper wick (2x+ body). After downtrend.",
        "psychology": "Bulls tried to push up, bears resisted, but bears may be exhausted",
        "confirmation_needed": True,
    },

    "shooting_star": {
        "type": "single", "signal": "bearish_reversal", "reliability": 0.70,
        "description": "Small body at bottom, long upper wick (2x+ body). After uptrend.",
        "psychology": "Bulls pushed price high but bears rejected the move strongly",
        "best_context": "At resistance, after strong rally",
        "confirmation_needed": True,
    },

    "hanging_man": {
        "type": "single", "signal": "bearish_reversal", "reliability": 0.65,
        "description": "Looks like hammer but appears AFTER uptrend. Warning sign.",
        "psychology": "Unusual selling pressure appearing — bears gaining foothold",
        "confirmation_needed": True,
    },

    "marubozu_bullish": {
        "type": "single", "signal": "bullish_continuation", "reliability": 0.75,
        "description": "Large bullish candle with no or tiny wicks. Full control by bulls.",
        "psychology": "Buyers dominated the entire session from open to close",
        "confirmation_needed": False,
        "volume_confirmation": "Essential — low volume weakens signal",
    },

    "marubozu_bearish": {
        "type": "single", "signal": "bearish_continuation", "reliability": 0.75,
        "description": "Large bearish candle with no or tiny wicks. Full control by bears.",
        "psychology": "Sellers dominated the entire session from open to close",
        "confirmation_needed": False,
    },

    "spinning_top": {
        "type": "single", "signal": "indecision", "reliability": 0.50,
        "description": "Small body, upper and lower wicks roughly equal. Neither side winning.",
        "bullish_context": "After downtrend = potential exhaustion of sellers",
        "bearish_context": "After uptrend = potential exhaustion of buyers",
    },

    # ── DOUBLE CANDLE PATTERNS ────────────────────────────────────────────

    "bullish_engulfing": {
        "type": "double", "signal": "bullish_reversal", "reliability": 0.80,
        "description": "Large bullish candle completely engulfs previous bearish candle.",
        "condition": "Must appear after downtrend",
        "psychology": "Bears gave up — bulls took complete control in one session",
        "volume_confirmation": "Strong volume on engulfing candle greatly increases reliability",
    },

    "bearish_engulfing": {
        "type": "double", "signal": "bearish_reversal", "reliability": 0.80,
        "description": "Large bearish candle completely engulfs previous bullish candle.",
        "condition": "Must appear after uptrend",
        "psychology": "Bulls gave up — bears took complete control in one session",
    },

    "bullish_harami": {
        "type": "double", "signal": "bullish_reversal", "reliability": 0.65,
        "description": "Small bullish candle inside previous large bearish candle.",
        "psychology": "Bearish momentum slowing, potential reversal building",
        "confirmation_needed": True,
    },

    "bearish_harami": {
        "type": "double", "signal": "bearish_reversal", "reliability": 0.65,
        "description": "Small bearish candle inside previous large bullish candle.",
        "psychology": "Bullish momentum slowing, potential reversal building",
        "confirmation_needed": True,
    },

    "piercing_line": {
        "type": "double", "signal": "bullish_reversal", "reliability": 0.72,
        "description": "After bearish candle, bullish opens below and closes above 50% of previous.",
        "psychology": "Bears lost control midway through session",
        "confirmation_needed": True,
    },

    "dark_cloud_cover": {
        "type": "double", "signal": "bearish_reversal", "reliability": 0.72,
        "description": "After bullish candle, bearish opens above and closes below 50% of previous.",
        "psychology": "Bulls lost control midway through session",
        "confirmation_needed": True,
    },

    "tweezer_bottom": {
        "type": "double", "signal": "bullish_reversal", "reliability": 0.68,
        "description": "Two candles with identical or very similar lows. Strong support confirmed.",
        "best_context": "At key support levels, after downtrend",
    },

    "tweezer_top": {
        "type": "double", "signal": "bearish_reversal", "reliability": 0.68,
        "description": "Two candles with identical or very similar highs. Strong resistance confirmed.",
        "best_context": "At key resistance levels, after uptrend",
    },

    # ── TRIPLE CANDLE PATTERNS ───────────────────────────────────────────

    "morning_star": {
        "type": "triple", "signal": "bullish_reversal", "reliability": 0.85,
        "description": "Bearish candle → small/doji candle with gap → bullish candle closing above 50% of first.",
        "psychology": "Bears exhausted → indecision → bulls take control",
        "best_context": "After prolonged downtrend, at support",
        "confirmation_needed": False,
    },

    "evening_star": {
        "type": "triple", "signal": "bearish_reversal", "reliability": 0.85,
        "description": "Bullish candle → small/doji candle with gap → bearish candle closing below 50% of first.",
        "psychology": "Bulls exhausted → indecision → bears take control",
        "best_context": "After prolonged uptrend, at resistance",
        "confirmation_needed": False,
    },

    "three_white_soldiers": {
        "type": "triple", "signal": "bullish_reversal_strong", "reliability": 0.85,
        "description": "Three consecutive bullish marubozu candles with higher closes.",
        "psychology": "Sustained, powerful buying pressure — trend change confirmed",
        "volume_confirmation": "Should see increasing volume across all three",
    },

    "three_black_crows": {
        "type": "triple", "signal": "bearish_reversal_strong", "reliability": 0.85,
        "description": "Three consecutive bearish marubozu candles with lower closes.",
        "psychology": "Sustained, powerful selling pressure — trend change confirmed",
    },

    "three_inside_up": {
        "type": "triple", "signal": "bullish_reversal", "reliability": 0.75,
        "description": "Bearish candle → harami → confirmation bullish close above first.",
        "psychology": "Gradual shift of power from bears to bulls",
    },

    "three_inside_down": {
        "type": "triple", "signal": "bearish_reversal", "reliability": 0.75,
        "description": "Bullish candle → harami → confirmation bearish close below first.",
        "psychology": "Gradual shift of power from bulls to bears",
    },

    "rising_three_methods": {
        "type": "triple+", "signal": "bullish_continuation", "reliability": 0.78,
        "description": "Large bullish candle → 3 small bearish candles within range → strong bullish breakout.",
        "psychology": "Brief consolidation within uptrend — buyers resting before next leg up",
    },

    "falling_three_methods": {
        "type": "triple+", "signal": "bearish_continuation", "reliability": 0.78,
        "description": "Large bearish candle → 3 small bullish candles within range → strong bearish breakdown.",
        "psychology": "Brief consolidation within downtrend — sellers resting before next leg down",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 2. CHART PATTERNS — Complete Encyclopedia
# ═══════════════════════════════════════════════════════════════════════════

CHART_PATTERNS = {

    # ── REVERSAL PATTERNS ──────────────────────────────────────────────────

    "head_and_shoulders": {
        "type": "reversal", "direction": "bearish", "reliability": 0.85,
        "timeframe_preference": "1h, 4h, daily",
        "description": "Three peaks: left shoulder < head > right shoulder, neckline support",
        "entry": "Break below neckline with volume",
        "target": "Measured move = head height from neckline",
        "stop_loss": "Above right shoulder",
        "failure_rate": 0.20,
        "nifty_occurrence": "Common at major NIFTY tops (18000, 18800 zones historically)",
    },

    "inverse_head_and_shoulders": {
        "type": "reversal", "direction": "bullish", "reliability": 0.85,
        "description": "Three troughs: left shoulder > head < right shoulder",
        "entry": "Break above neckline with volume",
        "target": "Measured move = head depth from neckline",
        "stop_loss": "Below right shoulder",
    },

    "double_top": {
        "type": "reversal", "direction": "bearish", "reliability": 0.80,
        "description": "Two peaks at similar levels. Second peak = lower volume = exhaustion.",
        "entry": "Break below the valley between the two tops",
        "target": "Measured move = pattern height",
        "psychology": "Bulls tried twice to break resistance, failed both times",
    },

    "double_bottom": {
        "type": "reversal", "direction": "bullish", "reliability": 0.80,
        "description": "Two troughs at similar levels. Second trough = lower volume = exhaustion.",
        "entry": "Break above the peak between the two bottoms (neckline)",
        "target": "Measured move = pattern height",
        "psychology": "Bears tried twice to break support, failed both times",
    },

    "triple_top": {
        "type": "reversal", "direction": "bearish", "reliability": 0.82,
        "description": "Three attempts at same resistance — all rejected. Very strong resistance.",
        "entry": "Break below support with volume",
    },

    "triple_bottom": {
        "type": "reversal", "direction": "bullish", "reliability": 0.82,
        "description": "Three attempts at same support — all held. Very strong support.",
        "entry": "Break above resistance with volume",
    },

    "rounding_bottom": {
        "type": "reversal", "direction": "bullish", "reliability": 0.75,
        "description": "Gradual U-shaped recovery. Slow shift from selling to buying.",
        "timeframe_preference": "Daily, weekly",
        "nifty_note": "Common in sector recovery plays",
    },

    "rounding_top": {
        "type": "reversal", "direction": "bearish", "reliability": 0.75,
        "description": "Gradual inverted U-shape. Slow shift from buying to selling.",
        "warning": "Hard to identify in real-time, easier in hindsight",
    },

    # ── CONTINUATION PATTERNS ─────────────────────────────────────────────

    "bull_flag": {
        "type": "continuation", "direction": "bullish", "reliability": 0.75,
        "description": "Strong upward move (pole) → brief consolidation/pullback (flag) → breakout",
        "entry": "Break above flag upper boundary",
        "target": "Pole length added to breakout point",
        "timing": "Flag should last 3-20 bars. Longer = weaker signal",
        "volume": "Drop during flag, spike on breakout",
        "intraday_nifty": "Very common on 5m/15m charts after news-driven spikes",
    },

    "bear_flag": {
        "type": "continuation", "direction": "bearish", "reliability": 0.75,
        "description": "Strong downward move (pole) → brief consolidation/bounce (flag) → breakdown",
        "entry": "Break below flag lower boundary",
        "target": "Pole length subtracted from breakdown point",
    },

    "bull_pennant": {
        "type": "continuation", "direction": "bullish", "reliability": 0.78,
        "description": "Strong move → converging trendlines (pennant) → breakout",
        "difference_from_flag": "Pennant has converging lines, flag has parallel lines",
        "volume": "Shrinking during pennant, explosion on breakout",
    },

    "bear_pennant": {
        "type": "continuation", "direction": "bearish", "reliability": 0.78,
        "description": "Strong bearish move → converging trendlines → breakdown",
    },

    "ascending_triangle": {
        "type": "continuation", "direction": "bullish", "reliability": 0.76,
        "description": "Flat top resistance + rising lows. Buyers getting more aggressive.",
        "entry": "Break above flat resistance with volume",
        "psychology": "Each pullback is shallower — bulls gaining control",
    },

    "descending_triangle": {
        "type": "continuation", "direction": "bearish", "reliability": 0.76,
        "description": "Flat bottom support + falling highs. Sellers getting more aggressive.",
        "entry": "Break below flat support with volume",
    },

    "symmetrical_triangle": {
        "type": "continuation", "direction": "neutral", "reliability": 0.70,
        "description": "Converging trendlines, each side equal. Breakout could be either way.",
        "entry": "Trade the breakout direction with volume confirmation",
        "bias": "Usually continues prior trend",
    },

    "cup_and_handle": {
        "type": "continuation", "direction": "bullish", "reliability": 0.80,
        "description": "Rounded bottom (cup) → small pullback (handle) → breakout above cup lip",
        "target": "Cup depth added to breakout point",
        "timeframe_preference": "Daily, weekly — classic swing/positional pattern",
    },

    "rectangle": {
        "type": "continuation", "direction": "neutral", "reliability": 0.68,
        "description": "Price bouncing between horizontal support and resistance.",
        "entry": "Breakout direction with volume",
        "nifty_note": "NIFTY spends significant time in rectangles before trending",
    },

    # ── WEDGE PATTERNS ───────────────────────────────────────────────────

    "rising_wedge": {
        "type": "reversal", "direction": "bearish", "reliability": 0.72,
        "description": "Both trendlines rising but converging. Higher highs + higher lows, but shrinking.",
        "signal": "Despite upward movement, bears gaining strength — breakdown coming",
        "entry": "Break below lower trendline",
        "common_mistake": "Do not short prematurely — wait for break",
    },

    "falling_wedge": {
        "type": "reversal", "direction": "bullish", "reliability": 0.72,
        "description": "Both trendlines falling but converging. Lower highs + lower lows, but shrinking.",
        "signal": "Despite downward movement, bulls gaining strength — breakout coming",
        "entry": "Break above upper trendline",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 3. MULTI-TIMEFRAME ANALYSIS RULES
# ═══════════════════════════════════════════════════════════════════════════

MTF_RULES = {
    "hierarchy": {
        "description": "Higher timeframe ALWAYS overrides lower timeframe",
        "order": ["monthly", "weekly", "daily", "4h", "1h", "15m", "5m", "1m"],
        "rule": "Only trade when ALL timeframes agree, or at minimum higher TF not opposing",
    },

    "alignment_framework": {
        "perfect_long": {
            "daily": "Uptrend (price above 200 EMA, ADX > 25)",
            "1h":    "Pullback to support complete, candle reversal signal",
            "5m":    "BUY signal, momentum turning up",
            "action": "High conviction BUY — all timeframes aligned",
        },
        "perfect_short": {
            "daily": "Downtrend (price below 200 EMA, ADX > 25)",
            "1h":    "Rally to resistance complete, candle reversal signal",
            "5m":    "SELL signal, momentum turning down",
            "action": "High conviction SELL — all timeframes aligned",
        },
        "conflicted": {
            "rule": "Daily bullish but 5m bearish = avoid. Wait for alignment.",
            "best_trade": "When 3+ timeframes agree = highest probability",
        },
    },

    "nifty_timeframe_guide": {
        "monthly": "Macro trend direction — bull/bear market phase",
        "weekly":  "Major support/resistance, swing trade direction",
        "daily":   "Primary trend, key levels, positional bias",
        "1h":      "Intraday bias, entry/exit zones",
        "15m":     "Refine entries, identify patterns",
        "5m":      "Execution timeframe for intraday",
        "1m":      "Scalping only — noisy, use sparingly",
    },

    "confluence_scoring": {
        "description": "Score each trade 0-10 based on alignment",
        "score_10": "All 5 timeframes aligned + volume + pattern + key level",
        "score_8":  "4 timeframes aligned + volume confirmation",
        "score_6":  "3 timeframes aligned",
        "score_below_5": "Avoid — too much conflict",
        "rule": "Only trade score >= 7 for NIFTY intraday options",
    },

    "higher_tf_bias": {
        "weekly_above_ema20": "Bias = LONG. Only take call option setups on 5m.",
        "weekly_below_ema20": "Bias = SHORT. Only take put option setups on 5m.",
        "daily_trending": "Trade with trend. Fade = higher risk.",
        "daily_ranging": "Wait for breakout or trade range extremes only.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 4. OPEN INTEREST (OI) ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

OI_ANALYSIS = {

    "price_oi_matrix": {
        "description": "The 4-quadrant OI analysis — most powerful OI tool",
        "quadrant_1": {
            "price": "rising", "oi": "rising",
            "interpretation": "LONG BUILDUP — Bullish. New longs entering.",
            "action": "Buy calls, ride the trend up",
        },
        "quadrant_2": {
            "price": "falling", "oi": "rising",
            "interpretation": "SHORT BUILDUP — Bearish. New shorts entering.",
            "action": "Buy puts, sell calls, ride down",
        },
        "quadrant_3": {
            "price": "rising", "oi": "falling",
            "interpretation": "SHORT COVERING — Moderately bullish. Shorts exiting.",
            "action": "Cautious long — move may not sustain (short covering ≠ fresh buying)",
        },
        "quadrant_4": {
            "price": "falling", "oi": "falling",
            "interpretation": "LONG UNWINDING — Bearish. Longs exiting.",
            "action": "Caution on longs — bearish but may not lead to new lows",
        },
    },

    "max_pain": {
        "description": "Strike at which option writers (MMs) lose least money on expiry",
        "rule": "Price tends to gravitate toward max pain as expiry approaches",
        "strongest_effect": "Last 2 days before expiry",
        "nifty_application": "On expiry day, expect NIFTY to test max pain level",
        "trap_warning": "Max pain shifts intraday — use as guide not as target",
    },

    "pcr_analysis": {
        "description": "Put-Call Ratio = Total Put OI / Total Call OI",
        "ranges": {
            "pcr_below_0.7": "Extremely bullish sentiment → contrarian SELL signal (too many calls = complacency)",
            "pcr_0.7_to_1.0": "Neutral to slight bullish bias",
            "pcr_1.0_to_1.2": "Neutral — balanced market",
            "pcr_1.2_to_1.5": "Slight bearish bias but support may hold",
            "pcr_above_1.5": "Extremely bearish sentiment → contrarian BUY signal (too many puts = panic)",
        },
        "pcr_trend": "PCR rising with price rising = healthy bullish trend",
        "pcr_divergence": "Price rising but PCR falling = bearish divergence — caution",
    },

    "iv_analysis": {
        "description": "Implied Volatility — the 'fear gauge' of options",
        "high_iv": {
            "definition": "IV > 20% (India VIX > 20 for NIFTY)",
            "meaning": "Market expecting big moves. Options expensive.",
            "strategy": "Sell options (premium decay) or buy straddles/strangles",
        },
        "low_iv": {
            "definition": "IV < 12% (India VIX < 12)",
            "meaning": "Complacency. Market calm. Options cheap.",
            "strategy": "Buy options. Low IV = cheap insurance. Breakout likely.",
            "warning": "Low IV periods end in explosive moves",
        },
        "iv_crush": {
            "description": "IV drops sharply after event (earnings, RBI policy, budget)",
            "impact": "Option buyers lose even if directionally correct",
            "rule": "Never buy options into known events — IV is priced in",
        },
        "iv_skew": {
            "description": "Difference in IV between put and call strikes",
            "positive_skew": "Puts more expensive = market fearful of downside",
            "negative_skew": "Calls more expensive = market fearful of missing upside",
        },
    },

    "support_resistance_from_oi": {
        "description": "Highest OI strike = strong support/resistance",
        "call_max_oi": "Strike with highest CALL OI = strong resistance (writers defend it)",
        "put_max_oi":  "Strike with highest PUT OI = strong support (writers defend it)",
        "rule": "NIFTY rarely closes beyond max OI strike on weekly expiry",
        "breakout": "If price breaks max OI strike with volume = explosive move likely",
        "nifty_insight": "Market makers (option writers) defend their positions — creates S/R",
    },

    "oi_change_alerts": {
        "fresh_call_writing": "Sharp rise in OI at call strike near ATM = cap being built → short",
        "fresh_put_writing":  "Sharp rise in OI at put strike near ATM = floor being built → long",
        "call_unwinding":     "OI falling at call strikes as price rises = resistance gone → long",
        "put_unwinding":      "OI falling at put strikes as price falls = support gone → short",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 5. TECHNICAL INDICATORS — Deep Interpretation
# ═══════════════════════════════════════════════════════════════════════════

INDICATOR_KNOWLEDGE = {

    "adx": {
        "full_name": "Average Directional Index",
        "measures": "Trend STRENGTH (not direction)",
        "levels": {
            "0-20":  "No trend / ranging market. Avoid trend-following strategies.",
            "20-25": "Trend forming. Weak but emerging.",
            "25-50": "Strong trend. Best environment for trend-following.",
            "50+":   "Very strong trend. Possible exhaustion ahead.",
        },
        "di_cross_rules": {
            "di_plus_crosses_above_di_minus": "Bullish — buy signal when ADX > 20",
            "di_minus_crosses_above_di_plus": "Bearish — sell signal when ADX > 20",
            "adx_rising": "Trend strengthening",
            "adx_falling": "Trend weakening even if DI still shows direction",
        },
        "mistake": "Buying DI cross when ADX < 20 = false signal in ranging market",
    },

    "rsi": {
        "full_name": "Relative Strength Index",
        "period": 14,
        "levels": {
            "above_70": "Overbought — potential reversal or slowdown",
            "50_70":    "Bullish momentum zone",
            "50":       "Neutral — no clear momentum",
            "30_50":    "Bearish momentum zone",
            "below_30": "Oversold — potential reversal or bounce",
        },
        "advanced_signals": {
            "bullish_divergence": "Price makes lower low, RSI makes higher low = bullish reversal warning",
            "bearish_divergence": "Price makes higher high, RSI makes lower high = bearish reversal warning",
            "failure_swing":      "RSI fails to exceed previous high = trend weakening",
            "hidden_divergence":  "Price higher low, RSI lower low = trend continuation (bullish)",
        },
        "nifty_levels": {
            "50_as_support": "In bull trends, RSI bounces from 40-50 zone",
            "50_as_resistance": "In bear trends, RSI rejected from 50-60 zone",
        },
    },

    "macd": {
        "full_name": "Moving Average Convergence Divergence",
        "components": {
            "macd_line": "12 EMA - 26 EMA",
            "signal_line": "9 EMA of MACD line",
            "histogram": "MACD - Signal",
        },
        "signals": {
            "bullish_crossover": "MACD crosses above signal = buy",
            "bearish_crossover": "MACD crosses below signal = sell",
            "zero_cross_up":     "MACD crosses above zero = trend turning bullish",
            "zero_cross_down":   "MACD crosses below zero = trend turning bearish",
            "histogram_growing": "Momentum accelerating in direction",
            "histogram_shrinking": "Momentum decelerating — potential reversal",
            "divergence":        "Most powerful signal — price vs MACD divergence",
        },
    },

    "bollinger_bands": {
        "full_name": "Bollinger Bands",
        "settings": "20 period SMA ± 2 standard deviations",
        "signals": {
            "price_at_upper_band": "Overbought in the short term — but can 'walk the band' in trends",
            "price_at_lower_band": "Oversold in the short term — potential bounce",
            "band_squeeze":        "Bands narrowing = volatility contraction → explosive move coming",
            "band_expansion":      "Bands widening = high volatility — trend in motion",
            "w_bottom":            "Two lows with second low inside bands = strong reversal",
            "m_top":               "Two highs with second high inside bands = strong reversal",
        },
        "bb_walk": "In strong trends, price walks the upper/lower band — not a sell/buy alone",
    },

    "vwap": {
        "full_name": "Volume Weighted Average Price",
        "importance": "THE most important intraday level for institutional reference",
        "rules": {
            "price_above_vwap": "Institutional buyers in control — long bias",
            "price_below_vwap": "Institutional sellers in control — short bias",
            "retest_from_above": "Price drops to VWAP and bounces = strong long entry",
            "retest_from_below": "Price rallies to VWAP and rejects = strong short entry",
            "vwap_breakout": "Price breaks through VWAP = potential trend change",
        },
        "intraday_nifty": "First cross of VWAP in morning session often sets intraday tone",
    },

    "cpr": {
        "full_name": "Central Pivot Range (TC-BC)",
        "components": {
            "pivot": "(H+L+C)/3 of previous day",
            "bc": "Bottom of Central Pivot = (H+L)/2",
            "tc": "Top of Central Pivot = Pivot + (Pivot - BC)",
        },
        "signals": {
            "price_above_tc": "Bullish bias for the day",
            "price_below_bc": "Bearish bias for the day",
            "price_inside_cpr": "Consolidation/indecision expected",
            "narrow_cpr": "Less than 0.15% of price = expect volatile trending day",
            "wide_cpr": "More than 0.3% of price = expect ranging day",
        },
        "nifty_insight": "CPR is used by professional Indian traders extensively — major institutional reference",
        "virgin_cpr": "CPR untested from previous day = price will likely test it",
    },

    "fibonacci": {
        "key_levels": {
            "23.6%": "Shallow retracement — very strong trend",
            "38.2%": "First major support in uptrend — ideal buy zone",
            "50.0%": "Psychological level — not Fibonacci but widely watched",
            "61.8%": "Golden ratio — strongest Fib level, high probability reversal",
            "78.6%": "Deep retracement — near reversal or trend change",
            "127.2%": "Extension target 1",
            "161.8%": "Extension target 2 — golden ratio extension",
        },
        "nifty_rule": "NIFTY respects 50% and 61.8% retracements remarkably well in swing trades",
        "confluence": "Fib level + S/R + EMA + Volume node = very high probability zone",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 6. TRADER PSYCHOLOGY & BEHAVIORAL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

TRADER_PSYCHOLOGY = {

    "cognitive_biases": {
        "loss_aversion": {
            "description": "Losses feel 2x worse than equivalent gains feel good",
            "market_impact": "Traders hold losing positions too long, cut winners too early",
            "ai_solution": "Fixed exit rules — stop loss must be non-negotiable",
        },
        "confirmation_bias": {
            "description": "Seeing only what confirms existing view",
            "market_impact": "Ignoring signals that contradict open position",
            "ai_solution": "AI evaluates ALL signals regardless of current position",
        },
        "recency_bias": {
            "description": "Overweighting recent events — after big loss, too cautious; after win, too aggressive",
            "market_impact": "Revenge trading, overconfidence cycles",
            "ai_solution": "ML model trained on full historical data, not recency-weighted",
        },
        "anchoring": {
            "description": "Over-relying on first price seen (e.g., 'I bought at 22000, it must go back')",
            "market_impact": "Holding losers because of entry price anchor",
        },
        "gambler_fallacy": {
            "description": "After 5 consecutive losses, believing 'the next must be a win'",
            "market_impact": "Increasing bet size after losing streak = account blowup",
        },
        "herd_mentality": {
            "description": "Following the crowd without independent analysis",
            "market_impact": "Buying tops and selling bottoms",
            "ai_solution": "Contrarian signals embedded in sentiment analysis",
        },
    },

    "market_crowd_psychology": {
        "euphoria": {
            "description": "Maximum optimism — everyone is bullish, news is all positive",
            "market_phase": "TOP. Smart money distributing to retail.",
            "indicators": "RSI >75, high IV calls, all news bullish, social media euphoric",
            "action": "Start reducing longs, watch for reversal patterns",
        },
        "panic": {
            "description": "Maximum pessimism — everyone is bearish, fear everywhere",
            "market_phase": "BOTTOM. Smart money accumulating.",
            "indicators": "RSI <25, VIX spike, put/call ratio > 1.5, media screaming 'crash'",
            "action": "Watch for reversal signals, potential contrarian buy",
        },
        "wall_of_worry": {
            "description": "Bull market climbing despite constant negative news",
            "rule": "Bull markets climb a wall of worry. Negative news = buy the dip.",
        },
        "slope_of_hope": {
            "description": "Bear market declining despite occasional positive news",
            "rule": "Bear markets slide the slope of hope. Positive news = sell the rally.",
        },
    },

    "smart_money_concepts": {
        "accumulation": {
            "description": "Institutions quietly buying at low prices, hiding footprint",
            "signs": "High volume at lows, multiple tests of support that hold, shrinking volatility",
        },
        "distribution": {
            "description": "Institutions quietly selling at high prices",
            "signs": "High volume at highs, multiple tests of resistance that fail, price stalls",
        },
        "stop_hunt": {
            "description": "Price briefly spikes below obvious support or above obvious resistance to trigger stops",
            "recognition": "Quick spike + immediate reversal = stop hunt",
            "opportunity": "If you survive the stop hunt, opposite position is high probability",
        },
        "order_blocks": {
            "description": "Zones where institutions placed large orders",
            "identification": "Last bearish candle before major up move = bullish order block",
            "rule": "Price often returns to order block before continuing in original direction",
        },
        "fair_value_gaps": {
            "description": "Gaps in price where market moved too fast (no trading occurred)",
            "rule": "Market tends to fill fair value gaps — targets for price return",
        },
    },

    "trading_rules_psychology": {
        "never_average_down": "Adding to losing positions = emotional decision, not analytical",
        "let_profits_run": "Trailing stops better than fixed targets in trending markets",
        "position_sizing": "Risk only 1-2% per trade. Not 10-20%.",
        "revenge_trading": "After a loss, take a break. Next trade will be emotional.",
        "journal_importance": "Without a trading journal, you cannot identify your patterns",
        "best_trades_feel_easy": "Forced trades = usually losing trades. Wait for A+ setups.",
        "correlation_risk": "Multiple correlated positions = single position risk. Diversify.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 7. NEWS IMPACT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

NEWS_IMPACT = {

    "high_impact_events": {
        "rbi_policy": {
            "description": "RBI Monetary Policy Committee decisions",
            "market_impact": "HIGH — can move NIFTY 1-3% on decision day",
            "rate_hike": "Negative for equity — higher cost of capital",
            "rate_cut": "Positive for equity — lower cost of capital, stimulus",
            "pause_hawkish": "Mild negative — hike may come later",
            "pause_dovish": "Mild positive — rate cut cycle may begin",
            "pre_event_rule": "IV rises before RBI — sell options 2 days before, buy back after",
        },
        "budget": {
            "description": "Union Budget — most important event for Indian markets",
            "market_impact": "VERY HIGH — can move 3-5% on day",
            "sectors_impacted": "Infrastructure, defence, FMCG, auto, banking based on allocations",
            "pre_budget": "Markets usually rally in expectation",
            "post_budget": "'Buy the rumour, sell the news' often applies",
        },
        "us_fed": {
            "description": "US Federal Reserve decisions — global risk sentiment driver",
            "market_impact": "HIGH — NIFTY follows global cues",
            "rate_hike": "Negative — FII outflows from EM, stronger dollar",
            "rate_cut": "Positive — FII inflows, risk-on",
            "dot_plot_hawkish": "Negative for NIFTY even without immediate rate change",
        },
        "cpi_inflation": {
            "description": "Consumer Price Index data",
            "higher_than_expected": "Negative — forces rate hikes, earnings pressure",
            "lower_than_expected": "Positive — rate cuts possible, multiple expansion",
        },
        "gdp_data": {
            "description": "GDP growth rate",
            "strong_gdp": "Positive — corporate earnings outlook improves",
            "weak_gdp": "Negative — earnings risk, possible policy easing (mixed)",
        },
        "fii_dii_activity": {
            "description": "Foreign and Domestic Institutional flows",
            "fii_buying": "Bullish — large net buyers = market support",
            "fii_selling": "Bearish — especially sustained selling over multiple days",
            "dii_buying": "Partially offsets FII selling, provides floor",
            "rule": "Net FII over 5-day period more important than single day",
        },
    },

    "sector_catalysts": {
        "banking": ["RBI policy", "NPA data", "credit growth", "interest rate changes"],
        "it": ["US tech earnings", "USD/INR rate", "US growth data", "visa policies"],
        "auto": ["GST changes", "oil prices", "EV policy", "monsoon (rural demand)"],
        "pharma": ["USFDA approvals", "drug pricing policies", "patent cliffs"],
        "metals": ["China PMI", "global commodity prices", "domestic infrastructure spend"],
        "realty": ["RBI rates", "affordable housing policies", "cement/steel prices"],
    },

    "sentiment_scoring": {
        "very_positive": {
            "examples": ["surprise rate cut", "strong GDP beat", "record FII inflows", "major reform"],
            "expected_move": "+1.5% to +3%",
            "options_play": "Buy ITM calls before open, take profit by 11am",
        },
        "positive": {
            "examples": ["in-line results with upside guidance", "dovish RBI", "FII buying"],
            "expected_move": "+0.5% to +1.5%",
        },
        "neutral": {
            "examples": ["in-line expectations", "no surprise"],
            "expected_move": "±0.3%",
        },
        "negative": {
            "examples": ["rate hike surprise", "earnings miss", "global sell-off"],
            "expected_move": "-0.5% to -1.5%",
        },
        "very_negative": {
            "examples": ["war escalation", "major political crisis", "global crash", "black swan"],
            "expected_move": "-2% to -5%+",
            "options_play": "Buy OTM puts, VIX spike = IV crush after event passes",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 8. MARKET STRUCTURE — Dow Theory + Wyckoff + SMC
# ═══════════════════════════════════════════════════════════════════════════

MARKET_STRUCTURE = {

    "dow_theory": {
        "primary_trend": "Months to years — the major bull/bear market",
        "secondary_trend": "Weeks to months — corrections/rallies within primary",
        "minor_trend": "Days to weeks — noise within secondary",
        "confirmation": "Both NSE and BSE must confirm a new trend (or major indices)",
        "volume_principle": "Volume must confirm price: rising volume in trend direction = healthy",
        "higher_highs_higher_lows": "Definition of uptrend",
        "lower_highs_lower_lows": "Definition of downtrend",
        "trend_change": "In uptrend: first lower high = warning. Lower low = confirmed reversal.",
    },

    "wyckoff_phases": {
        "accumulation": {
            "phase_a": "Selling climax — heavy selling, smart money begins buying",
            "phase_b": "Building cause — ranging, smart money accumulating",
            "phase_c": "Spring — final bearish trap, price dips below range then recovers",
            "phase_d": "Demand takes control, price rises within range",
            "phase_e": "Markup — price breaks out, uptrend begins",
        },
        "distribution": {
            "phase_a": "Buying climax — heavy buying, smart money begins selling",
            "phase_b": "Building cause — ranging, smart money distributing",
            "phase_c": "UTAD — final bullish trap, price spikes above range then fails",
            "phase_d": "Supply takes control, price falls within range",
            "phase_e": "Markdown — price breaks down, downtrend begins",
        },
        "wyckoff_rule": "Large effort (volume) → small result (price move) = trend reversal near",
    },

    "support_resistance_rules": {
        "old_resistance_becomes_support": "After breakout, resistance flips to support — classic retest opportunity",
        "old_support_becomes_resistance": "After breakdown, support flips to resistance — sell the retest",
        "round_numbers": "Psychological levels (22000, 22500, 23000) = strong S/R",
        "previous_swing_highs_lows": "Natural S/R levels",
        "volume_profile_poc": "Price of Control = level with most volume traded = magnet",
        "strength_of_level": "More times tested = stronger (but also more prone to break)",
        "level_freshness": "Fresh levels (never tested) > old levels (repeatedly tested)",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 9. NIFTY-SPECIFIC BEHAVIORAL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

NIFTY_SPECIFIC = {

    "intraday_patterns": {
        "opening_range": {
            "description": "First 15-30 minutes after 9:15 establishes the day's range",
            "rule": "Breakout above opening high or below opening low = direction for the day",
            "confirmation": "Wait for 9:30-9:45 before trading opening range breakout",
        },
        "gap_rules": {
            "gap_up_rule": "Gap up > 0.5% = likely test of gap fill or hold. Wait for 9:30.",
            "gap_down_rule": "Gap down > 0.5% = likely test of gap fill or continued selling.",
            "gap_fill_probability": "70% of gaps fill within the same day on NIFTY",
            "island_reversal": "Gap + gap in opposite direction = strong reversal signal",
        },
        "lunch_hour": {
            "timing": "12:00 - 13:30 IST",
            "behavior": "Lower volume, erratic movement, avoid trading",
            "rule": "No new positions during lunch hour unless strong signal",
        },
        "expiry_week": {
            "monday": "Theta burns options — sell premium if range-bound",
            "tuesday": "Direction usually emerges — follow the breakout",
            "wednesday": "Max pain becomes relevant — watch for gravitational pull",
            "thursday": "Expiry day — high volatility morning, possible max pain close",
            "rule": "Last hour of expiry = avoid — unpredictable pinning/violent moves",
        },
        "monthly_patterns": {
            "first_week": "Usually direction from monthly expiry carries over",
            "mid_month": "FII/DII activity data releases — can shift sentiment",
            "last_week": "Expiry-related volatility increases",
            "budget_month": "January-February extremely volatile",
        },
    },

    "nifty_correlations": {
        "sgx_nifty": "Singapore Nifty futures — best pre-market gap indicator",
        "dow_jones": "Strong correlation (0.7+) — US market direction = NIFTY opening gap",
        "india_vix": "VIX > 20 = volatile day expected, VIX < 12 = calm day",
        "usd_inr": "INR weakening = FII outflows = NIFTY pressure",
        "crude_oil": "High crude = inflation = bearish (India is net importer)",
        "bank_nifty": "BANKNIFTY leads NIFTY 70% of the time — monitor as early indicator",
    },

    "key_levels_methodology": {
        "weekly_pivots": "More important than daily for NIFTY swing",
        "previous_week_high_low": "Breakout above = bullish, below = bearish",
        "option_chain_levels": "Highest call OI = resistance, highest put OI = support",
        "psychological_levels": "Every 500 points = major psychological level on NIFTY",
        "gap_zones": "Unfilled gaps = target zones",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS — Used by AI brain to look up knowledge
# ═══════════════════════════════════════════════════════════════════════════

def get_pattern_knowledge(pattern_name: str) -> dict:
    """Look up knowledge about a specific candlestick or chart pattern."""
    result = CANDLESTICK_PATTERNS.get(pattern_name, {})
    if not result:
        result = CHART_PATTERNS.get(pattern_name, {})
    return result


def get_indicator_signal_meaning(indicator: str, condition: str) -> str:
    """Get the interpretation of an indicator in a specific condition."""
    ind = INDICATOR_KNOWLEDGE.get(indicator, {})
    if not ind:
        return f"No knowledge for indicator: {indicator}"
    signals = ind.get("signals", ind.get("levels", {}))
    return signals.get(condition, f"No specific rule for {indicator} + {condition}")


def classify_news_impact(headline: str) -> dict:
    """Classify a news headline's likely market impact."""
    headline_lower = headline.lower()
    high_impact_keywords = {
        "very_positive": ["rate cut", "stimulus", "record gdp", "surprise profit", "major reform", "fdi approval"],
        "positive": ["rate hold dovish", "gdp growth", "fii buying", "earnings beat", "policy support"],
        "very_negative": ["war", "crisis", "crash", "collapse", "default", "sanctions", "black swan"],
        "negative": ["rate hike", "inflation surge", "earnings miss", "fii selling", "global recession"],
    }
    for sentiment, keywords in high_impact_keywords.items():
        if any(kw in headline_lower for kw in keywords):
            return {"sentiment": sentiment, "details": NEWS_IMPACT["sentiment_scoring"].get(sentiment, {})}
    return {"sentiment": "neutral", "details": NEWS_IMPACT["sentiment_scoring"]["neutral"]}


def get_oi_interpretation(price_change: str, oi_change: str) -> dict:
    """Interpret OI data based on price and OI movement."""
    key_map = {
        ("rising", "rising"):  "quadrant_1",
        ("falling", "rising"): "quadrant_2",
        ("rising", "falling"): "quadrant_3",
        ("falling", "falling"): "quadrant_4",
    }
    key = key_map.get((price_change, oi_change), "quadrant_1")
    return OI_ANALYSIS["price_oi_matrix"].get(key, {})


def get_full_context_for_ai(signal_data: dict) -> str:
    """
    Generate full market context string for AI models.
    This is what gets sent to GPT/Gemini/Claude for enhanced analysis.
    """
    context = f"""
MARKET KNOWLEDGE CONTEXT FOR AI ANALYSIS:

CURRENT SIGNAL: {signal_data.get('signal', 'HOLD')} | Confidence: {signal_data.get('confidence', 0):.1%}
PRICE: ₹{signal_data.get('price', 0):,.0f}
ADX: {signal_data.get('adx', 0):.1f} — {INDICATOR_KNOWLEDGE['adx']['levels'].get('25-50', '') if signal_data.get('adx', 0) > 25 else INDICATOR_KNOWLEDGE['adx']['levels']['0-20']}
RSI: {signal_data.get('rsi', 50):.1f}
REGIME: {signal_data.get('regime', 'UNKNOWN')}

OI FRAMEWORK:
- Price ↑ + OI ↑ = {OI_ANALYSIS['price_oi_matrix']['quadrant_1']['interpretation']}
- Price ↓ + OI ↑ = {OI_ANALYSIS['price_oi_matrix']['quadrant_2']['interpretation']}

NIFTY INTRADAY RULES:
- VWAP: {INDICATOR_KNOWLEDGE['vwap']['rules']['price_above_vwap']}
- CPR: {INDICATOR_KNOWLEDGE['cpr']['signals']['price_above_tc']}
- Expiry: {NIFTY_SPECIFIC['intraday_patterns']['expiry_week']['thursday']}

PSYCHOLOGY CHECK:
- Current bias risk: {TRADER_PSYCHOLOGY['cognitive_biases']['confirmation_bias']['ai_solution']}

REASONING FROM AI: {', '.join(signal_data.get('reasoning', []))}
"""
    return context.strip()
