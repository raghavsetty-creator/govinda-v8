"""
NIFTY AI Trading System - Feature Engineering
===============================================
Computes all technical indicators and derived features.
These become the "eyes" of the AI model.
"""

import pandas as pd
import numpy as np
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Transforms raw OHLCV data into ML-ready feature matrix.
    Features are grouped into:
      - Trend indicators
      - Momentum indicators
      - Volatility indicators
      - Volume indicators
      - Price structure (CPR, Pivots)
      - Market regime
      - Time-based features
    """

    def __init__(self):
        self.feature_names = []

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Master function: takes raw OHLCV, returns feature-enriched DataFrame.
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for feature computation")
            return df

        df = df.copy()

        df = self._trend_features(df)
        df = self._momentum_features(df)
        df = self._volatility_features(df)
        df = self._volume_features(df)
        df = self._price_structure_features(df)
        df = self._regime_features(df)
        df = self._time_features(df)
        df = self._candle_pattern_features(df)

        # Drop rows with NaN from indicator warmup period
        df = df.replace([np.inf, -np.inf], np.nan)
        base_features = [f for f in config.FEATURES if f in df.columns]
        df = df.dropna(subset=base_features)

        self.feature_names = config.FEATURES
        logger.info(f"Feature matrix: {len(df)} rows × {len(config.FEATURES)} features")
        return df

    # ─────────────────────────────────────────
    # TREND FEATURES
    # ─────────────────────────────────────────

    def _trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ADX, DI+, DI- for trend direction and strength."""

        high  = df["high"]
        low   = df["low"]
        close = df["close"]
        period = 14

        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low  - close.shift(1)).abs()
        tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        dm_plus  = high - high.shift(1)
        dm_minus = low.shift(1) - low

        dm_plus  = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)

        # Smoothed (Wilder's method)
        atr_s   = tr.ewm(alpha=1/period, min_periods=period).mean()
        dmp_s   = dm_plus.ewm(alpha=1/period, min_periods=period).mean()
        dmm_s   = dm_minus.ewm(alpha=1/period, min_periods=period).mean()

        df["di_plus"]  = 100 * dmp_s / atr_s
        df["di_minus"] = 100 * dmm_s / atr_s

        dx = 100 * (df["di_plus"] - df["di_minus"]).abs() / (df["di_plus"] + df["di_minus"] + 1e-9)
        df["adx"] = dx.ewm(alpha=1/period, min_periods=period).mean()

        # ADX trend flag: 1=bullish trend, -1=bearish trend, 0=no trend
        df["adx_trend"] = np.where(
            (df["adx"] > config.MIN_ADX_FOR_TRADE) & (df["di_plus"] > df["di_minus"]), 1,
            np.where(
                (df["adx"] > config.MIN_ADX_FOR_TRADE) & (df["di_minus"] > df["di_plus"]), -1,
                0
            )
        )

        # EMAs for trend confirmation
        df["ema_9"]  = close.ewm(span=9, adjust=False).mean()
        df["ema_21"] = close.ewm(span=21, adjust=False).mean()
        df["ema_50"] = close.ewm(span=50, adjust=False).mean()
        df["ema_cross"] = np.where(df["ema_9"] > df["ema_21"], 1, -1)

        return df

    # ─────────────────────────────────────────
    # MOMENTUM FEATURES
    # ─────────────────────────────────────────

    def _momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI, MACD, Stochastics."""

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        # RSI (14)
        delta = close.diff()
        gain  = delta.where(delta > 0, 0)
        loss  = (-delta).where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        df["rsi"] = 100 - 100 / (1 + rs)

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"]        = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"]   = df["macd"] - df["macd_signal"]

        # Stochastic (14, 3)
        lowest_low   = low.rolling(14).min()
        highest_high = high.rolling(14).max()
        df["stoch_k"] = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-9)
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        # ROC - Rate of change
        df["roc_5"]  = close.pct_change(5)  * 100
        df["roc_10"] = close.pct_change(10) * 100

        return df

    # ─────────────────────────────────────────
    # VOLATILITY FEATURES
    # ─────────────────────────────────────────

    def _volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ATR, Bollinger Bands."""

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        # ATR (14)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low  - close.shift(1)).abs()
        tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"]     = tr.ewm(alpha=1/14, adjust=False).mean()
        df["atr_pct"] = df["atr"] / close * 100   # ATR as % of price

        # Bollinger Bands (20, 2)
        bb_mid        = close.rolling(20).mean()
        bb_std        = close.rolling(20).std()
        df["bb_upper"] = bb_mid + 2 * bb_std
        df["bb_lower"] = bb_mid - 2 * bb_std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (bb_mid + 1e-9)
        df["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)

        return df

    # ─────────────────────────────────────────
    # VOLUME FEATURES
    # ─────────────────────────────────────────

    def _volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """OBV, VWAP deviation."""

        close  = df["close"]
        volume = df["volume"]
        high   = df["high"]
        low    = df["low"]

        # OBV change (relative)
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        df["obv_change"] = obv.pct_change(5).fillna(0)

        # VWAP (intraday - reset each day)
        typical_price = (high + low + close) / 3
        df["vwap"] = (
            (typical_price * volume).groupby(df.index.date).cumsum() /
            volume.groupby(df.index.date).cumsum()
        )
        df["vwap_deviation"] = (close - df["vwap"]) / (df["vwap"] + 1e-9) * 100

        # Volume ratio (current vs 20-bar avg)
        df["volume_ratio"] = volume / (volume.rolling(20).mean() + 1e-9)

        return df

    # ─────────────────────────────────────────
    # PRICE STRUCTURE (CPR + PIVOTS)
    # ─────────────────────────────────────────

    def _price_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Central Pivot Range (CPR) and Pivot Points.
        Calculated on previous day's data, applied to current day.
        """

        close = df["close"]

        # Group by date to get daily OHLC
        daily = df.groupby(df.index.date).agg(
            high_d  = ("high",  "max"),
            low_d   = ("low",   "min"),
            close_d = ("close", "last"),
        )

        # Pivot Points from previous day
        daily["pivot"]    = (daily["high_d"] + daily["low_d"] + daily["close_d"]) / 3
        daily["r1"]       = 2 * daily["pivot"] - daily["low_d"]
        daily["s1"]       = 2 * daily["pivot"] - daily["high_d"]
        daily["r2"]       = daily["pivot"] + (daily["high_d"] - daily["low_d"])
        daily["s2"]       = daily["pivot"] - (daily["high_d"] - daily["low_d"])

        # CPR
        daily["bc"]       = (daily["high_d"] + daily["low_d"]) / 2
        daily["tc"]       = (daily["pivot"] - daily["bc"]) + daily["pivot"]
        daily["cpr_width"] = (daily["tc"] - daily["bc"]).abs() / daily["pivot"] * 100

        # Shift by 1 day (use previous day's pivots for current day)
        daily = daily.shift(1)

        # Map daily pivot data back to intraday bars
        for col in ["pivot", "r1", "s1", "r2", "s2", "bc", "tc", "cpr_width"]:
            df[col] = df.index.map(lambda x: daily.get(col, {}).get(x.date(), np.nan))

        # Position relative to CPR and Pivot
        df["cpr_position"]   = np.where(
            close > df["tc"], 1,
            np.where(close < df["bc"], -1, 0)
        )
        df["pivot_position"] = np.where(close > df["pivot"], 1, -1)

        return df

    # ─────────────────────────────────────────
    # REGIME FEATURES
    # ─────────────────────────────────────────

    def _regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Market regime: trending, ranging, volatile."""

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        # Higher highs / Lower lows (swing structure)
        df["higher_high"]  = (high > high.shift(1)).astype(int)
        df["lower_low"]    = (low  < low.shift(1)).astype(int)
        df["trending_up"]   = (
            (close > df["ema_21"]) & (df["ema_21"] > df["ema_50"]) & (df["adx"] > 25)
        ).astype(int)
        df["trending_down"] = (
            (close < df["ema_21"]) & (df["ema_21"] < df["ema_50"]) & (df["adx"] > 25)
        ).astype(int)

        # Price compression (low ATR = ranging market)
        df["ranging"] = (df["atr_pct"] < df["atr_pct"].rolling(20).mean() * 0.7).astype(int)

        return df

    # ─────────────────────────────────────────
    # TIME FEATURES
    # ─────────────────────────────────────────

    def _time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Time-of-day features — NIFTY has strong intraday seasonality."""

        df["hour"]            = df.index.hour
        df["minute"]          = df.index.minute
        df["is_first_hour"]   = ((df["hour"] == 9) | ((df["hour"] == 10) & (df["minute"] < 15))).astype(int)
        df["is_last_hour"]    = (df["hour"] >= 14).astype(int)
        df["minutes_to_close"] = (15 * 60 + 30 - df["hour"] * 60 - df["minute"]).clip(lower=0)
        df["day_of_week"]     = df.index.dayofweek  # 0=Mon, 4=Fri

        return df

    # ─────────────────────────────────────────
    # CANDLE PATTERN FEATURES
    # ─────────────────────────────────────────

    def _candle_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Japanese candlestick-derived features."""

        body   = (df["close"] - df["open"]).abs()
        total  = df["high"] - df["low"] + 1e-9
        upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
        lower_wick = df[["open", "close"]].min(axis=1) - df["low"]

        df["candle_body_ratio"] = body / total
        df["wick_ratio"]        = (upper_wick - lower_wick) / total
        df["is_bullish_candle"] = (df["close"] > df["open"]).astype(int)

        # Gap from previous close
        df["gap_pct"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1) * 100

        return df

    # ─────────────────────────────────────────
    # LABEL CREATION (for training)
    # ─────────────────────────────────────────

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates target labels for supervised learning.

        Label = 1 (BUY)   if price rises >= PROFIT_TARGET_PCT in next N bars
        Label = 2 (SELL)  if price falls >= PROFIT_TARGET_PCT in next N bars
        Label = 0 (HOLD)  otherwise

        Uses config.LOOKFORWARD_BARS and config.PROFIT_TARGET_PCT.
        """
        n      = config.LOOKFORWARD_BARS
        target = config.PROFIT_TARGET_PCT
        close  = df["close"]

        future_max = close.shift(-1).rolling(n).max().shift(-(n-1))
        future_min = close.shift(-1).rolling(n).min().shift(-(n-1))

        buy_signal  = (future_max - close) / close >= target
        sell_signal = (close - future_min) / close >= target

        df["label"] = 0
        df.loc[buy_signal,  "label"] = 1
        df.loc[sell_signal, "label"] = 2
        # When both conditions met, choose the stronger one
        both = buy_signal & sell_signal
        df.loc[both & (future_max - close > close - future_min), "label"] = 1
        df.loc[both & (close - future_min > future_max - close), "label"] = 2

        # Drop last N rows (no future data)
        df = df.iloc[:-n]

        label_dist = df["label"].value_counts().to_dict()
        logger.info(f"Label distribution: HOLD={label_dist.get(0,0)} BUY={label_dist.get(1,0)} SELL={label_dist.get(2,0)}")
        return df
