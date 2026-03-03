"""
NIFTY AI Trading System - Data Fetcher
=======================================
Fetches OHLCV data from multiple sources.
Primary: yfinance (free, works immediately)
Secondary: Dhan API hook (plug in your token)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime, timedelta
import pytz
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class DataFetcher:
    """
    Unified data fetcher supporting multiple sources.
    Automatically falls back to yfinance if broker API not configured.
    """

    def __init__(self):
        self.source = self._detect_source()
        self.cache  = {}
        logger.info(f"DataFetcher initialized | source={self.source}")

    def _detect_source(self):
        if config.DHAN_ACCESS_TOKEN:
            return "dhan"
        elif config.ZERODHA_API_KEY:
            return "zerodha"
        else:
            return "yfinance"

    # ─────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────

    def fetch_historical(self, period: str = None, interval: str = None) -> pd.DataFrame:
        """Fetch historical OHLCV. Returns clean DataFrame."""
        period   = period   or config.HISTORICAL_PERIOD
        interval = interval or config.TIMEFRAME

        logger.info(f"Fetching historical data | period={period} interval={interval}")

        if self.source == "yfinance":
            return self._fetch_yfinance(period, interval)
        elif self.source == "dhan":
            return self._fetch_dhan_historical(period, interval)
        else:
            return self._fetch_yfinance(period, interval)  # fallback

    def fetch_latest_candles(self, n: int = 100) -> pd.DataFrame:
        """Fetch the most recent N candles for live signal generation."""
        df = self._fetch_yfinance("5d", config.TIMEFRAME)
        return df.tail(n) if df is not None and len(df) >= n else df

    def fetch_vix(self) -> pd.DataFrame:
        """Fetch India VIX data."""
        try:
            vix = yf.download("^INDIAVIX", period="60d", interval="1d", progress=False)
            vix = vix[["Close"]].rename(columns={"Close": "vix"})
            vix.index = vix.index.tz_localize(None)
            return vix
        except Exception as e:
            logger.warning(f"VIX fetch failed: {e}")
            return pd.DataFrame()

    def get_market_status(self) -> dict:
        """Check if market is currently open."""
        now = datetime.now(IST)
        open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        is_open = (
            now.weekday() < 5 and  # Mon-Fri
            open_time <= now <= close_time
        )
        return {
            "is_open": is_open,
            "current_time": now.strftime("%H:%M:%S IST"),
            "session": "OPEN" if is_open else "CLOSED",
            "minutes_to_close": max(0, int((close_time - now).seconds / 60)) if is_open else 0,
        }

    # ─────────────────────────────────────────
    # YFINANCE SOURCE
    # ─────────────────────────────────────────

    def _fetch_yfinance(self, period: str, interval: str) -> pd.DataFrame:
        """Download from Yahoo Finance and clean up."""
        try:
            ticker = yf.Ticker(config.SYMBOL)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                logger.error("yfinance returned empty data")
                return pd.DataFrame()

            # Standardize columns
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.columns = ["open", "high", "low", "close", "volume"]

            # Remove timezone info for consistency
            if df.index.tz is not None:
                df.index = df.index.tz_convert(IST).tz_localize(None)

            # Filter trading hours only
            df = self._filter_trading_hours(df)

            # Remove bad rows
            df = df.replace([np.inf, -np.inf], np.nan).dropna()
            df = df[df["volume"] > 0]

            logger.info(f"Fetched {len(df)} candles from yfinance")
            return df

        except Exception as e:
            logger.error(f"yfinance fetch error: {e}")
            return pd.DataFrame()

    def _filter_trading_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only candles within NSE trading hours."""
        if df.empty:
            return df
        times = df.index.time
        start = pd.Timestamp(config.TRADING_START).time()
        end   = pd.Timestamp(config.TRADING_END).time()
        mask  = (times >= start) & (times <= end)
        return df[mask]

    # ─────────────────────────────────────────
    # DHAN API SOURCE (hook - fill your token)
    # ─────────────────────────────────────────

    def _fetch_dhan_historical(self, period: str, interval: str) -> pd.DataFrame:
        """
        Dhan API historical data fetcher.
        Docs: https://dhanhq.co/docs/v2/
        Fill config.DHAN_CLIENT_ID and config.DHAN_ACCESS_TOKEN to activate.
        """
        try:
            import requests
            headers = {
                "access-token": config.DHAN_ACCESS_TOKEN,
                "client-id":    config.DHAN_CLIENT_ID,
                "Content-Type": "application/json",
            }

            # Map interval to Dhan format
            interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
            dhan_interval = interval_map.get(interval, "5")

            # Calculate date range
            end_date   = datetime.now()
            days_back  = int(period.replace("d", "")) if "d" in period else 60
            start_date = end_date - timedelta(days=days_back)

            payload = {
                "securityId": "13",          # NIFTY 50 security ID on Dhan
                "exchangeSegment": "IDX_I",
                "instrument": "INDEX",
                "interval": dhan_interval,
                "oi": "false",
                "fromDate": start_date.strftime("%Y-%m-%d"),
                "toDate": end_date.strftime("%Y-%m-%d"),
            }

            response = requests.post(
                "https://api.dhan.co/v2/charts/intraday",
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame({
                    "open":   data["open"],
                    "high":   data["high"],
                    "low":    data["low"],
                    "close":  data["close"],
                    "volume": data["volume"],
                }, index=pd.to_datetime(data["timestamp"], unit="s"))
                df.index = df.index.tz_localize("UTC").tz_convert(IST).tz_localize(None)
                logger.info(f"Fetched {len(df)} candles from Dhan API")
                return df
            else:
                logger.warning(f"Dhan API error {response.status_code}, falling back to yfinance")
                return self._fetch_yfinance(period, interval)

        except Exception as e:
            logger.warning(f"Dhan fetch failed: {e}, falling back to yfinance")
            return self._fetch_yfinance(period, interval)

    # ─────────────────────────────────────────
    # UTILS
    # ─────────────────────────────────────────

    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """Save fetched data to CSV for offline use."""
        os.makedirs(config.DATA_DIR, exist_ok=True)
        filename = filename or f"nifty_{config.TIMEFRAME}_{datetime.now().strftime('%Y%m%d')}.csv"
        path = os.path.join(config.DATA_DIR, filename)
        df.to_csv(path)
        logger.info(f"Saved data to {path}")
        return path

    def load_from_csv(self, path: str) -> pd.DataFrame:
        """Load previously saved data."""
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        logger.info(f"Loaded {len(df)} rows from {path}")
        return df
