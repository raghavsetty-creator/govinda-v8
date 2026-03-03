"""
GOVINDA NIFTY AI Trading System v8 — Master Configuration
==========================================================
All secrets loaded from environment variables.
In production, Azure Key Vault injects them at startup.
Never hardcode secrets here.
"""
import os

# ─────────────────────────────────────────────────────────
# ENVIRONMENT
# ─────────────────────────────────────────────────────────
ENV          = os.getenv("GOVINDA_ENV", "development")   # development | production
AZURE_REGION = os.getenv("AZURE_REGION", "centralindia")

# ─────────────────────────────────────────────────────────
# INSTRUMENT
# ─────────────────────────────────────────────────────────
SYMBOL         = "^NSEI"
SYMBOL_DISPLAY = "NIFTY 50"
TIMEFRAME      = "5m"
TRADING_START  = "09:15"
TRADING_END    = "15:30"
TIMEZONE       = "Asia/Kolkata"

# ─────────────────────────────────────────────────────────
# LOT SIZES — NSE Circular FAOP70616 (Effective Jan 6 2026)
# SEBI/HO/MRD-PoD2/CIR/P/2024/00181
# ─────────────────────────────────────────────────────────
LOT_SIZES = {
    "NIFTY":      65,    # Reduced from 75 on Jan 6 2026
    "BANKNIFTY":  30,    # Reduced from 35 on Jan 6 2026
    "FINNIFTY":   60,    # Reduced from 65 on Jan 6 2026
    "MIDCPNIFTY": 120,   # Reduced from 140 on Jan 6 2026
    "NIFTYNXT50": 25,    # Unchanged
    "SENSEX":     20,    # Unchanged
}
NIFTY_LOT_SIZE = LOT_SIZES["NIFTY"]   # 65 — use this throughout
MAX_LOTS       = 5                     # Hard cap per trade
DEFAULT_LOTS   = 1

# ─────────────────────────────────────────────────────────
# RISK MANAGEMENT
# ─────────────────────────────────────────────────────────
TRADING_CAPITAL        = float(os.getenv("TRADING_CAPITAL", "500000"))  # ₹5L
RISK_PER_TRADE_PCT     = 0.02    # 2% max risk per trade
MAX_DAILY_LOSS_PCT     = 0.05    # 5% daily drawdown → halt
MAX_DAILY_SIGNALS      = 10
MAX_CONSECUTIVE_LOSSES = 3
MIN_ADX_FOR_TRADE      = 20
MIN_SIGNAL_CONFIDENCE  = 0.60
MIN_MTF_CONFLUENCE     = 6       # Min MTF score (0–10) to enter

# ─────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────
HISTORICAL_PERIOD   = "60d"
LIVE_FETCH_INTERVAL = 60
DATA_DIR            = os.getenv("DATA_DIR", "/opt/govinda/data")
MIN_TRAINING_ROWS   = 500

# ─────────────────────────────────────────────────────────
# FEATURES
# ─────────────────────────────────────────────────────────
FEATURES = [
    "adx","di_plus","di_minus","adx_trend",
    "rsi","macd","macd_signal","macd_hist","stoch_k","stoch_d",
    "atr","atr_pct","bb_upper","bb_lower","bb_width","bb_position",
    "obv_change","vwap_deviation",
    "cpr_position","pivot_position","candle_body_ratio","wick_ratio",
    "higher_high","lower_low","trending_up","trending_down",
    "hour","minute","is_first_hour","is_last_hour","minutes_to_close",
]

# ─────────────────────────────────────────────────────────
# SIGNAL
# ─────────────────────────────────────────────────────────
BUY_THRESHOLD   = 0.62
SELL_THRESHOLD  = 0.62
SIGNAL_COOLDOWN = 3

# ─────────────────────────────────────────────────────────
# ML MODEL
# ─────────────────────────────────────────────────────────
MODEL_TYPE         = "lightgbm"
MODEL_DIR          = os.getenv("MODEL_DIR", "/opt/govinda/models")
RETRAIN_INTERVAL   = "daily"
RETRAIN_AFTER_BARS = 100
LOOKFORWARD_BARS   = 6
PROFIT_TARGET_PCT  = 0.003
ONLINE_LEARNING    = True

LGBM_PARAMS = {
    "n_estimators":300,"learning_rate":0.05,"max_depth":6,
    "num_leaves":31,"subsample":0.8,"colsample_bytree":0.8,
    "min_child_samples":20,"reg_alpha":0.1,"reg_lambda":0.1,
    "class_weight":"balanced","random_state":42,"verbose":-1,
}
XGB_PARAMS = {
    "n_estimators":300,"learning_rate":0.05,"max_depth":5,
    "subsample":0.8,"colsample_bytree":0.8,"use_label_encoder":False,
    "eval_metric":"logloss","random_state":42,"verbosity":0,
}

# ─────────────────────────────────────────────────────────
# BROKER API — via env / Azure Key Vault
# ─────────────────────────────────────────────────────────
DHAN_CLIENT_ID     = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN  = os.getenv("DHAN_ACCESS_TOKEN", "")
FYERS_APP_ID       = os.getenv("FYERS_APP_ID", "")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")
ZERODHA_API_KEY    = os.getenv("ZERODHA_API_KEY", "")
ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET", "")

# ─────────────────────────────────────────────────────────
# AI API KEYS — via env / Azure Key Vault
# ─────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")

# ─────────────────────────────────────────────────────────
# AZURE
# ─────────────────────────────────────────────────────────
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_KEY_VAULT_URL             = os.getenv("AZURE_KEY_VAULT_URL", "")
AZURE_BLOB_LOGS                 = "govinda-logs"
AZURE_BLOB_MODELS               = "govinda-models"
AZURE_BLOB_SIGNALS              = "govinda-signals"

# ─────────────────────────────────────────────────────────
# NOTIFICATIONS (Telegram)
# ─────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
NOTIFY_ON_SIGNAL   = os.getenv("NOTIFY_ON_SIGNAL", "true").lower() == "true"
NOTIFY_ON_ERROR    = os.getenv("NOTIFY_ON_ERROR",  "true").lower() == "true"

# ─────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────
LOG_DIR             = os.getenv("LOG_DIR", "/opt/govinda/logs")
LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "/opt/govinda/mlruns")
EXPERIMENT_NAME     = "GOVINDA_NIFTY_AI_v8"
