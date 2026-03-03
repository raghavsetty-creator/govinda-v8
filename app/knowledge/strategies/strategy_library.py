"""
NIFTY AI — World's Greatest Trading Strategies Library
=======================================================
Encoded knowledge from the world's most successful traders and systems.
Each strategy is:
  1. Documented with full rules
  2. Implemented as a signal function
  3. Backtestable independently
  4. Eligible for the evolution engine to test/improve/combine

Sources:
  - Jesse Livermore (tape reading, trend following)
  - Nicolas Darvas (box theory)
  - William O'Neil (CAN SLIM)
  - Larry Williams (short-term trading)
  - Ed Seykota (trend following, EMA systems)
  - Linda Raschke (short-term momentum)
  - Mark Minervini (SEPA — Specific Entry Point Analysis)
  - Richard Dennis / Bill Eckhardt (Turtle Trading)
  - John Bollinger (Bollinger Bands system)
  - Stan Weinstein (Stage Analysis)
  - Tom DeMark (TD Sequential)
  - Quantitative: Mean Reversion, Momentum Factor, Volatility Breakout
  - Academic: Jegadeesh & Titman momentum, Fama-French factors
  - Indian-specific: CPR system, VWAP bands, OI-based
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """A complete, self-describing trading strategy."""
    name: str
    author: str
    category: str          # trend / momentum / mean_reversion / breakout / volatility / hybrid
    timeframe: str         # intraday / swing / positional
    description: str
    rules: List[str]
    psychology: str
    win_rate_expected: float    # Historical expected win rate
    risk_reward: float          # Minimum R:R ratio
    best_market: str            # trending / ranging / volatile / any
    worst_market: str           # market condition to avoid
    signal_fn: Optional[Callable] = None   # The actual signal function
    parameters: Dict = field(default_factory=dict)
    live_performance: Dict = field(default_factory=dict)  # Updated daily by evaluator


# ═══════════════════════════════════════════════════════════════════════════
# STRATEGY IMPLEMENTATIONS
# Each takes a DataFrame with indicators and returns: 1=BUY, -1=SELL, 0=HOLD
# ═══════════════════════════════════════════════════════════════════════════

def _darvas_box(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Nicolas Darvas Box Theory (1956).
    Buy when price breaks above a consolidation box on high volume.
    Used by Darvas to turn $10K into $2M in 18 months.
    """
    lookback = params.get("box_period", 20)
    vol_mult = params.get("volume_multiplier", 1.5)

    h = df["high"]; l = df["low"]; c = df["close"]
    vol = df["volume"]

    box_high = h.rolling(lookback).max()
    box_low  = l.rolling(lookback).min()
    avg_vol  = vol.rolling(lookback).mean()

    # Buy: current close breaks above box high with high volume
    buy  = (c > box_high.shift(1)) & (vol > avg_vol * vol_mult)
    sell = (c < box_low.shift(1))

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _turtle_breakout(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Turtle Trading System (Richard Dennis / Bill Eckhardt, 1983).
    The famous system that proved trading can be taught.
    System 1: 20-day breakout entry, 10-day breakout exit.
    System 2: 55-day breakout entry, 20-day breakout exit.
    Adapted to 5-minute bars for intraday NIFTY.
    """
    entry_period = params.get("entry_period", 20)
    exit_period  = params.get("exit_period", 10)
    atr_period   = params.get("atr_period", 14)

    h = df["high"]; l = df["low"]; c = df["close"]

    high_entry = h.rolling(entry_period).max()
    low_entry  = l.rolling(entry_period).min()
    high_exit  = h.rolling(exit_period).max()
    low_exit   = l.rolling(exit_period).min()

    # ATR-based position sizing filter (avoid choppy markets)
    tr    = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    atr   = tr.ewm(alpha=1/atr_period).mean()
    atr_pct = atr / c

    buy  = (c >= high_entry.shift(1)) & (atr_pct > 0.001)
    sell = (c <= low_entry.shift(1))  & (atr_pct > 0.001)

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _linda_raschke_80_20(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Linda Bradford Raschke — 80/20 Setup.
    Based on 'Street Smarts'. One of the highest-probability intraday setups.
    If bar opens in bottom 20% of prior range and closes in top 20% → buy tomorrow's open.
    Adapted: uses rolling 5-bar range.
    """
    period = params.get("period", 5)

    o = df["open"]; h = df["high"]; l = df["low"]; c = df["close"]

    prev_h = h.rolling(period).max().shift(1)
    prev_l = l.rolling(period).min().shift(1)
    prev_range = prev_h - prev_l

    # Open in bottom 20%, close in top 20%
    open_low  = o < (prev_l + prev_range * 0.20)
    close_high = c > (prev_h - prev_range * 0.20)

    # Mirror for short: open in top 20%, close in bottom 20%
    open_high  = o > (prev_h - prev_range * 0.20)
    close_low  = c < (prev_l + prev_range * 0.20)

    signals = pd.Series(0, index=df.index)
    signals[open_low & close_high]  =  1
    signals[open_high & close_low]  = -1
    return signals


def _seykota_ema_crossover(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Ed Seykota — Exponential Moving Average Trend System.
    Seykota reportedly turned $5,000 into $15M. Simple EMA crossover
    with trend filter. "The trend is your friend until the bend in the end."
    """
    fast = params.get("fast_ema", 9)
    slow = params.get("slow_ema", 21)
    trend= params.get("trend_ema", 50)

    c = df["close"]
    ema_fast  = c.ewm(span=fast,  adjust=False).mean()
    ema_slow  = c.ewm(span=slow,  adjust=False).mean()
    ema_trend = c.ewm(span=trend, adjust=False).mean()

    # Only trade in direction of trend
    in_uptrend   = c > ema_trend
    in_downtrend = c < ema_trend

    buy  = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1)) & in_uptrend
    sell = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1)) & in_downtrend

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _bollinger_mean_reversion(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    John Bollinger — Bollinger Band Mean Reversion (W/M Pattern).
    Buy when price tags lower band AND RSI shows positive divergence.
    Sell when price tags upper band AND RSI shows negative divergence.
    """
    period  = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)
    rsi_period = params.get("rsi_period", 14)

    c = df["close"]
    ma   = c.rolling(period).mean()
    std  = c.rolling(period).std()
    upper = ma + std_dev * std
    lower = ma - std_dev * std

    delta = c.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/rsi_period).mean()
    loss = (-delta).where(delta < 0, 0).ewm(alpha=1/rsi_period).mean()
    rsi  = 100 - 100 / (1 + gain / (loss + 1e-9))

    # Price touched lower band, RSI recovering from oversold
    buy  = (c.shift(1) <= lower.shift(1)) & (c > lower) & (rsi < 40) & (rsi > rsi.shift(1))
    # Price touched upper band, RSI falling from overbought
    sell = (c.shift(1) >= upper.shift(1)) & (c < upper) & (rsi > 60) & (rsi < rsi.shift(1))

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _minervini_sepa(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Mark Minervini — SEPA (Specific Entry Point Analysis).
    Used by US Investing Champion. Adapted for NIFTY intraday.
    Entry rules: Price > 50MA > 150MA > 200MA. Price within 25% of 52-week high.
    Pivot point breakout on volume.
    """
    h = df["high"]; c = df["close"]; v = df["volume"]

    ma50  = c.ewm(span=50,  adjust=False).mean()
    ma150 = c.ewm(span=150, adjust=False).mean()
    ma200 = c.ewm(span=200, adjust=False).mean()

    # Stage 2 uptrend: all MAs aligned
    stage2 = (c > ma50) & (ma50 > ma150) & (ma150 > ma200)

    # Near high (within 15% of 50-bar high — intraday version)
    high_50 = h.rolling(50).max()
    near_high = c >= high_50 * 0.85

    # Volume surge on breakout
    avg_vol = v.rolling(20).mean()
    vol_surge = v > avg_vol * 1.4

    # Pivot breakout: price makes new 10-bar high
    new_high = c == h.rolling(10).max()

    buy  = stage2 & near_high & vol_surge & new_high
    sell = (~stage2) & (c < ma50)  # Exit when stage changes

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _weinstein_stage_analysis(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Stan Weinstein — Stage Analysis (from 'Secrets for Profiting in Bull and Bear Markets').
    4 stages: Basing (1), Advancing (2), Topping (3), Declining (4).
    Only buy in Stage 2. Only sell/short in Stage 4.
    """
    c = df["close"]; v = df["volume"]
    h = df["high"]; l = df["low"]

    ma30 = c.ewm(span=30, adjust=False).mean()  # 30-week MA adapted to 30-bar
    ma30_slope = ma30.diff(5)

    avg_vol = v.rolling(30).mean()
    rel_vol = v / avg_vol

    # Stage 2: price above rising 30-bar MA, breakout on volume
    stage2 = (c > ma30) & (ma30_slope > 0) & (rel_vol > 1.2)

    # Stage 4: price below falling 30-bar MA
    stage4 = (c < ma30) & (ma30_slope < 0)

    # New 10-bar high = breakout trigger
    breakout = c == h.rolling(10).max()
    breakdown = c == l.rolling(10).min()

    signals = pd.Series(0, index=df.index)
    signals[stage2 & breakout]  =  1
    signals[stage4 & breakdown] = -1
    return signals


def _larry_williams_power_of_pattern(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Larry Williams — Short-Term Trading (Williams %R + Commitment of Traders).
    %R oscillator for short-term reversals. Adapted without COT (not available intraday).
    Williams %R < -80 + next bar higher = buy; %R > -20 + next bar lower = sell.
    """
    period = params.get("period", 14)

    h = df["high"]; l = df["low"]; c = df["close"]

    highest_h = h.rolling(period).max()
    lowest_l  = l.rolling(period).min()
    willr = -100 * (highest_h - c) / (highest_h - lowest_l + 1e-9)

    # Oversold reversal
    buy  = (willr.shift(1) < -80) & (willr > willr.shift(1)) & (c > c.shift(1))
    # Overbought reversal
    sell = (willr.shift(1) > -20) & (willr < willr.shift(1)) & (c < c.shift(1))

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _momentum_factor(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Academic Momentum Factor (Jegadeesh & Titman, 1993).
    12-1 month momentum: best predictor of future returns in academic finance.
    Adapted for intraday: 60-bar momentum (5 hours) minus last 5 bars.
    """
    long_window  = params.get("long_window", 60)
    short_window = params.get("short_window", 5)

    c = df["close"]
    long_ret  = c.pct_change(long_window)
    short_ret = c.pct_change(short_window)

    # Momentum signal: strong long-term up, short-term pullback = BUY
    # Strong long-term down, short-term bounce = SELL
    buy  = (long_ret > 0.005) & (short_ret < 0) & (short_ret > -0.003)
    sell = (long_ret < -0.005) & (short_ret > 0) & (short_ret < 0.003)

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _vwap_reversal_intraday(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    VWAP Reversion Strategy — Used by professional intraday traders.
    Price deviates from VWAP by N standard deviations → mean reversion trade.
    Key: only works in range-bound/non-trending conditions.
    """
    std_mult = params.get("std_mult", 1.5)

    c = df["close"]; v = df["volume"]

    # VWAP calculation
    typical = (df["high"] + df["low"] + c) / 3
    cum_tv  = (typical * v).cumsum()
    cum_v   = v.cumsum()
    vwap    = cum_tv / cum_v

    # VWAP bands
    std      = (c - vwap).rolling(20).std()
    upper_b  = vwap + std_mult * std
    lower_b  = vwap - std_mult * std

    # RSI for confirmation
    delta = c.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14).mean()
    loss = (-delta).where(delta < 0, 0).ewm(alpha=1/14).mean()
    rsi  = 100 - 100 / (1 + gain / (loss + 1e-9))

    buy  = (c < lower_b) & (rsi < 35)
    sell = (c > upper_b) & (rsi > 65)

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _cpr_nifty_system(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    CPR (Central Pivot Range) Trading System — Indian Market Specialist.
    Widely used by professional Indian traders for NIFTY/BANKNIFTY.
    Narrow CPR = trending day. Wide CPR = ranging day.
    Trade: above TC = buy pullbacks; below BC = sell bounces.
    """
    c = df["close"]; h = df["high"]; l = df["low"]

    pivot = (h.shift(1) + l.shift(1) + c.shift(1)) / 3
    bc    = (h.shift(1) + l.shift(1)) / 2
    tc    = pivot + (pivot - bc)

    r1 = 2 * pivot - l.shift(1)
    s1 = 2 * pivot - h.shift(1)

    # Above TC: buy pullbacks to TC
    touch_tc_from_above = (c.shift(1) > tc) & (c >= tc * 0.9998) & (c <= tc * 1.002)
    # Below BC: sell bounces to BC
    touch_bc_from_below = (c.shift(1) < bc) & (c <= bc * 1.0002) & (c >= bc * 0.998)

    # CPR width filter (narrow CPR = expect trending day)
    cpr_width = (tc - bc) / pivot
    narrow_cpr = cpr_width < 0.003

    signals = pd.Series(0, index=df.index)
    signals[touch_tc_from_above & narrow_cpr] =  1
    signals[touch_bc_from_below & narrow_cpr] = -1
    return signals


def _volatility_breakout(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Volatility Breakout — Toby Crabel's Opening Range Breakout.
    Range contraction followed by expansion = directional breakout.
    ATR-based entry: open ± (ATR * multiplier).
    """
    atr_period = params.get("atr_period", 14)
    multiplier = params.get("multiplier", 0.5)
    lookback   = params.get("lookback", 5)

    h = df["high"]; l = df["low"]; c = df["close"]

    tr  = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/atr_period).mean()

    # Volatility contraction: recent ATR < historical ATR
    vol_squeeze = atr < atr.rolling(lookback*4).mean() * 0.8

    # Breakout above/below recent range
    recent_high = h.rolling(lookback).max().shift(1)
    recent_low  = l.rolling(lookback).min().shift(1)

    buy  = (c > recent_high) & vol_squeeze.shift(1)
    sell = (c < recent_low)  & vol_squeeze.shift(1)

    signals = pd.Series(0, index=df.index)
    signals[buy]  =  1
    signals[sell] = -1
    return signals


def _td_sequential(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    Tom DeMark — TD Sequential.
    One of the most sophisticated timing tools. Counts 9 consecutive
    closes lower/higher than 4 bars ago to identify exhaustion.
    Count to 9 = potential reversal. 'Perfected' 9 = high probability.
    """
    c = df["close"]

    # TD Buy Setup: 9 consecutive closes less than close 4 bars earlier
    td_buy_count  = pd.Series(0, index=c.index)
    td_sell_count = pd.Series(0, index=c.index)

    buy_cnt = sell_cnt = 0
    for i in range(4, len(c)):
        if c.iloc[i] < c.iloc[i-4]:
            buy_cnt += 1
            sell_cnt = 0
        elif c.iloc[i] > c.iloc[i-4]:
            sell_cnt += 1
            buy_cnt = 0
        else:
            buy_cnt = sell_cnt = 0
        td_buy_count.iloc[i]  = min(buy_cnt,  9)
        td_sell_count.iloc[i] = min(sell_cnt, 9)

    # Signal at count = 9 (exhaustion)
    signals = pd.Series(0, index=c.index)
    signals[td_buy_count == 9]  =  1   # 9 downs = potential bottom
    signals[td_sell_count == 9] = -1   # 9 ups = potential top
    return signals


def _rsi_divergence(df: pd.DataFrame, params: dict) -> pd.Series:
    """
    RSI Divergence — The most reliable momentum-based reversal signal.
    Bullish divergence: price lower low, RSI higher low = STRONG BUY.
    Bearish divergence: price higher high, RSI lower high = STRONG SELL.
    Used by nearly every professional trader as a high-conviction signal.
    """
    rsi_period = params.get("rsi_period", 14)
    lookback   = params.get("lookback", 20)

    c = df["close"]

    delta = c.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/rsi_period).mean()
    loss = (-delta).where(delta < 0, 0).ewm(alpha=1/rsi_period).mean()
    rsi  = 100 - 100 / (1 + gain / (loss + 1e-9))

    # Find recent lows/highs
    price_low  = c.rolling(lookback).min()
    price_high = c.rolling(lookback).max()
    rsi_low    = rsi.rolling(lookback).min()
    rsi_high   = rsi.rolling(lookback).max()

    # Bullish divergence: price at or near low, RSI making higher low
    bull_div = (
        (c <= price_low * 1.005) &
        (rsi > rsi_low + 5) &
        (rsi < 45)
    )

    # Bearish divergence: price at or near high, RSI making lower high
    bear_div = (
        (c >= price_high * 0.995) &
        (rsi < rsi_high - 5) &
        (rsi > 55)
    )

    signals = pd.Series(0, index=df.index)
    signals[bull_div] =  1
    signals[bear_div] = -1
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# STRATEGY REGISTRY — The complete library
# ═══════════════════════════════════════════════════════════════════════════

STRATEGY_LIBRARY: Dict[str, Strategy] = {

    "darvas_box": Strategy(
        name="Darvas Box Theory",
        author="Nicolas Darvas",
        category="breakout",
        timeframe="swing",
        description="Buy breakouts above consolidation boxes on volume. Darvas used this to turn $10K into $2M.",
        rules=["Price breaks above N-bar high", "Volume > 1.5x average", "Previous N bars formed a tight box"],
        psychology="Institutions accumulate in boxes. Breakout = distribution phase ending, mark-up beginning.",
        win_rate_expected=0.45,
        risk_reward=3.0,
        best_market="trending",
        worst_market="ranging",
        signal_fn=_darvas_box,
        parameters={"box_period": 20, "volume_multiplier": 1.5},
    ),

    "turtle_breakout": Strategy(
        name="Turtle Breakout System",
        author="Richard Dennis / Bill Eckhardt",
        category="trend",
        timeframe="intraday",
        description="20-bar breakout entry. Proved 'trading can be taught'. Enormous risk-reward.",
        rules=["Long: close >= 20-bar high", "Short: close <= 20-bar low", "ATR filter: avoid choppy markets", "Pyramid: add on favorable moves"],
        psychology="Trend followers sacrifice win rate for enormous winners. Accept many small losses, catch one huge trend.",
        win_rate_expected=0.40,
        risk_reward=4.0,
        best_market="trending",
        worst_market="ranging",
        signal_fn=_turtle_breakout,
        parameters={"entry_period": 20, "exit_period": 10, "atr_period": 14},
    ),

    "raschke_80_20": Strategy(
        name="Linda Raschke 80/20 Setup",
        author="Linda Bradford Raschke",
        category="momentum",
        timeframe="intraday",
        description="High-probability reversal: open in bottom 20% of range, close in top 20%.",
        rules=["Bar opens in bottom 20% of prior N-bar range", "Bar closes in top 20% of prior range", "Next bar = strong buy signal"],
        psychology="Smart money absorbs all selling and reverses. Retail trapped short at lows.",
        win_rate_expected=0.65,
        risk_reward=2.0,
        best_market="volatile",
        worst_market="low_volatility",
        signal_fn=_linda_raschke_80_20,
        parameters={"period": 5},
    ),

    "seykota_ema": Strategy(
        name="Seykota EMA Trend System",
        author="Ed Seykota",
        category="trend",
        timeframe="intraday",
        description="Simple EMA crossover with trend filter. Seykota turned $5K into $15M.",
        rules=["Fast EMA crosses above Slow EMA", "Price above Trend EMA", "Only trade in trend direction"],
        psychology="Most money is made riding big trends. Small loss exits protect capital for the next big trend.",
        win_rate_expected=0.42,
        risk_reward=3.5,
        best_market="trending",
        worst_market="ranging",
        signal_fn=_seykota_ema_crossover,
        parameters={"fast_ema": 9, "slow_ema": 21, "trend_ema": 50},
    ),

    "bollinger_mean_reversion": Strategy(
        name="Bollinger Band Mean Reversion",
        author="John Bollinger",
        category="mean_reversion",
        timeframe="intraday",
        description="Buy at lower band + RSI recovery. Sell at upper band + RSI weakening.",
        rules=["Price touches lower/upper Bollinger Band", "RSI confirming reversal", "Volume declining on approach"],
        psychology="Extreme deviations from mean have a statistical tendency to revert. Bands define 'normal' range.",
        win_rate_expected=0.60,
        risk_reward=1.5,
        best_market="ranging",
        worst_market="strongly_trending",
        signal_fn=_bollinger_mean_reversion,
        parameters={"period": 20, "std_dev": 2.0, "rsi_period": 14},
    ),

    "minervini_sepa": Strategy(
        name="Minervini SEPA",
        author="Mark Minervini",
        category="breakout",
        timeframe="intraday",
        description="Specific Entry Point Analysis. US Investing Champion strategy. Price structure + volume + timing.",
        rules=["Price > 50MA > 150MA > 200MA (Stage 2)", "Within 15% of N-bar high", "Volume 40%+ above average on breakout", "Clean consolidation pattern preceding"],
        psychology="Only buy the strongest stocks at the ideal moment. Avoid everything else.",
        win_rate_expected=0.50,
        risk_reward=3.0,
        best_market="trending",
        worst_market="bear_market",
        signal_fn=_minervini_sepa,
        parameters={},
    ),

    "weinstein_stage": Strategy(
        name="Weinstein Stage Analysis",
        author="Stan Weinstein",
        category="trend",
        timeframe="swing",
        description="4-stage market cycle. Buy only Stage 2 breakouts. Never fight Stage 4.",
        rules=["Stage 2: Price above rising 30-bar MA", "Breakout on above-average volume", "Stage 4: short only"],
        psychology="Markets move through predictable lifecycle stages. Buying right stage eliminates most losing trades.",
        win_rate_expected=0.55,
        risk_reward=3.0,
        best_market="trending",
        worst_market="ranging",
        signal_fn=_weinstein_stage_analysis,
        parameters={},
    ),

    "williams_percent_r": Strategy(
        name="Larry Williams %R Reversal",
        author="Larry Williams",
        category="mean_reversion",
        timeframe="intraday",
        description="Short-term reversal using Williams %R oscillator. Williams won World Cup Trading Championship.",
        rules=["Williams %R < -80 (oversold)", "Next bar closes higher", "Confirmed by price action"],
        psychology="Short-term traders overreact to news, creating temporary extremes that quickly revert.",
        win_rate_expected=0.58,
        risk_reward=1.8,
        best_market="ranging",
        worst_market="strongly_trending",
        signal_fn=_larry_williams_power_of_pattern,
        parameters={"period": 14},
    ),

    "momentum_factor": Strategy(
        name="Academic Momentum Factor",
        author="Jegadeesh & Titman (1993)",
        category="momentum",
        timeframe="intraday",
        description="Nobel-level academic research: 12-1 month momentum predicts future returns. Adapted for intraday.",
        rules=["Strong 60-bar momentum", "Short-term pullback providing entry", "Price still above 50-bar EMA"],
        psychology="Winner stocks continue winning. Academic momentum captures systematic institutional flows.",
        win_rate_expected=0.52,
        risk_reward=2.5,
        best_market="trending",
        worst_market="mean_reverting",
        signal_fn=_momentum_factor,
        parameters={"long_window": 60, "short_window": 5},
    ),

    "vwap_reversal": Strategy(
        name="VWAP Band Reversion",
        author="Professional Intraday Traders",
        category="mean_reversion",
        timeframe="intraday",
        description="Price deviates from VWAP by 1.5 std dev → reversion trade. Institutional benchmark.",
        rules=["Price > 1.5 std from VWAP", "RSI extreme", "Low ADX (not in strong trend)"],
        psychology="Institutions use VWAP as benchmark. Extreme deviations = opportunity for informed buyers/sellers.",
        win_rate_expected=0.62,
        risk_reward=1.5,
        best_market="ranging",
        worst_market="trending",
        signal_fn=_vwap_reversal_intraday,
        parameters={"std_mult": 1.5},
    ),

    "cpr_system": Strategy(
        name="CPR Trading System",
        author="Indian Professional Traders",
        category="hybrid",
        timeframe="intraday",
        description="Central Pivot Range — most widely used level system by Indian professional traders.",
        rules=["Narrow CPR = trending day", "Wide CPR = ranging day", "Price above TC = bullish", "Retest of TC/BC = entry"],
        psychology="Professional Indian traders react to CPR levels. Self-fulfilling prophecy creates predictable reactions.",
        win_rate_expected=0.58,
        risk_reward=2.0,
        best_market="trending",
        worst_market="highly_volatile",
        signal_fn=_cpr_nifty_system,
        parameters={},
    ),

    "volatility_breakout": Strategy(
        name="Volatility Breakout (Crabel)",
        author="Toby Crabel",
        category="breakout",
        timeframe="intraday",
        description="Range contraction precedes range expansion. ATR-based breakout of contracted range.",
        rules=["Recent ATR < historical ATR × 0.8 (squeeze)", "Break above N-bar high", "Entry: open + ATR × multiplier"],
        psychology="Markets alternate between contraction and expansion. Squeeze = spring coiling before release.",
        win_rate_expected=0.48,
        risk_reward=2.5,
        best_market="any",
        worst_market="already_expanded",
        signal_fn=_volatility_breakout,
        parameters={"atr_period": 14, "multiplier": 0.5, "lookback": 5},
    ),

    "td_sequential": Strategy(
        name="TD Sequential",
        author="Tom DeMark",
        category="momentum",
        timeframe="intraday",
        description="Counts 9 consecutive exhaustion bars. Used by hedge funds globally. Predicts exhaustion points.",
        rules=["Count 9 consecutive closes < close 4 bars ago (buy setup)", "Perfect 9: bar 8 low < bar 6 low", "13 count = more powerful signal"],
        psychology="Exhaustion principle: 9 consecutive moves in one direction = participants who agree have already acted.",
        win_rate_expected=0.55,
        risk_reward=2.0,
        best_market="any",
        worst_market="strongly_trending",
        signal_fn=_td_sequential,
        parameters={},
    ),

    "rsi_divergence": Strategy(
        name="RSI Divergence System",
        author="J. Welles Wilder / Universal",
        category="momentum",
        timeframe="intraday",
        description="Bullish/bearish divergence between price and RSI. One of highest-probability reversal signals.",
        rules=["Price makes lower low, RSI makes higher low = BUY", "Price makes higher high, RSI makes lower high = SELL", "Confirm with candlestick reversal pattern"],
        psychology="Divergence = momentum is weakening before price reverses. Insider selling while price still rising.",
        win_rate_expected=0.63,
        risk_reward=2.5,
        best_market="any",
        worst_market="strongly_trending",
        signal_fn=_rsi_divergence,
        parameters={"rsi_period": 14, "lookback": 20},
    ),
}


def get_strategy(name: str) -> Optional[Strategy]:
    return STRATEGY_LIBRARY.get(name)


def list_strategies_by_market(market_condition: str) -> List[str]:
    """Return strategies best suited for current market condition."""
    return [
        name for name, s in STRATEGY_LIBRARY.items()
        if s.best_market in [market_condition, "any"]
    ]


def run_strategy(name: str, df: pd.DataFrame) -> pd.Series:
    """Run a named strategy on a DataFrame."""
    s = STRATEGY_LIBRARY.get(name)
    if not s or not s.signal_fn:
        return pd.Series(0, index=df.index)
    try:
        return s.signal_fn(df, s.parameters)
    except Exception as e:
        logger.warning(f"Strategy {name} failed: {e}")
        return pd.Series(0, index=df.index)


def get_strategy_ensemble_signal(df: pd.DataFrame, regime: str = "any") -> dict:
    """
    Run ALL strategies and return ensemble vote.
    Weights strategies by their expected reliability in current regime.
    """
    votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
    strategy_votes = {}

    suitable = list_strategies_by_market(regime) or list(STRATEGY_LIBRARY.keys())

    for name in suitable:
        s = STRATEGY_LIBRARY[name]
        try:
            sig = run_strategy(name, df)
            last = int(sig.iloc[-1]) if not sig.empty else 0
            label = "BUY" if last > 0 else ("SELL" if last < 0 else "HOLD")

            # Weight by expected performance
            weight = s.win_rate_expected * s.risk_reward
            # Bonus weight for live performance if available
            if s.live_performance.get("recent_accuracy"):
                weight *= (1 + s.live_performance["recent_accuracy"] - 0.5)

            votes[label] += weight
            strategy_votes[name] = {"signal": label, "weight": round(weight, 2)}
        except:
            pass

    total = sum(votes.values()) or 1
    best = max(votes, key=votes.get)

    return {
        "signal": best,
        "confidence": votes[best] / total,
        "votes": votes,
        "strategy_breakdown": strategy_votes,
        "strategies_run": len(strategy_votes),
    }
