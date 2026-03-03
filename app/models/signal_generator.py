"""
NIFTY AI Trading System - Self-Learning Signal Generator
=========================================================
Core AI engine that:
1. Trains on historical data
2. Generates BUY/SELL/HOLD signals with confidence
3. Continuously retrains as new market data arrives
4. Tracks its own performance and adapts
"""

import numpy as np
import pandas as pd
import joblib
import logging
import os
import json
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, accuracy_score, precision_score,
    recall_score, f1_score
)
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

SIGNAL_LABELS = {0: "HOLD", 1: "BUY", 2: "SELL"}
SIGNAL_COLORS = {0: "⚪", 1: "🟢", 2: "🔴"}


class SelfLearningSignalGenerator:
    """
    AI signal generator with continuous learning capability.

    Architecture:
    - Primary model: LightGBM (fast, handles feature importance well)
    - Secondary model: XGBoost (ensemble member)
    - Scaler: StandardScaler (fitted on training data)
    - Performance tracker: Rolling accuracy window
    - Auto-retrain: Triggered by time interval OR performance degradation
    """

    def __init__(self):
        self.model_lgbm    = None
        self.model_xgb     = None
        self.scaler        = StandardScaler()
        self.is_trained    = False
        self.feature_names = list(config.FEATURES)  # snapshot at init
        self.last_trained  = None
        self.bars_since_retrain = 0
        self.performance_log = []
        self.signal_history  = []
        self.new_data_buffer = []   # Accumulates new bars for online learning

        # Performance tracking
        self.metrics = {
            "train_accuracy": 0,
            "cv_accuracy": 0,
            "precision_buy": 0,
            "precision_sell": 0,
            "total_signals": 0,
            "correct_signals": 0,
            "rolling_accuracy": [],
        }

        os.makedirs(config.MODEL_DIR, exist_ok=True)
        self._try_load_saved_model()

    # ─────────────────────────────────────────
    # TRAINING
    # ─────────────────────────────────────────

    def train(self, df: pd.DataFrame, force: bool = False) -> dict:
        """
        Train the model on labeled feature data.
        Uses TimeSeriesSplit CV to prevent lookahead bias.
        """
        if not force and self.is_trained and not self._should_retrain():
            logger.info("Model up to date, skipping retrain")
            return self.metrics

        if "label" not in df.columns:
            logger.error("DataFrame must have 'label' column. Run FeatureEngineer.create_labels() first.")
            return {}

        # Validate features
        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            logger.error(f"Missing features: {missing}")
            return {}

        # Use only features available in this DataFrame
        available_features = [f for f in self.feature_names if f in df.columns]
        self.feature_names = available_features  # update to what was actually trained on
        
        X = df[self.feature_names].values
        y = df["label"].values

        if len(X) < config.MIN_TRAINING_ROWS:
            logger.warning(f"Only {len(X)} rows, need {config.MIN_TRAINING_ROWS}. Using available data.")

        logger.info(f"Training on {len(X)} samples | features={len(self.feature_names)}")
        logger.info(f"Class distribution: {pd.Series(y).value_counts().to_dict()}")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # TimeSeriesSplit cross-validation (no lookahead bias)
        tscv = TimeSeriesSplit(n_splits=5)

        # ── LightGBM ──
        self.model_lgbm = LGBMClassifier(**config.LGBM_PARAMS)
        cv_scores_lgbm  = cross_val_score(
            self.model_lgbm, X_scaled, y, cv=tscv, scoring="accuracy", n_jobs=-1
        )
        self.model_lgbm.fit(X_scaled, y)

        # ── XGBoost ──
        self.model_xgb = XGBClassifier(**config.XGB_PARAMS)
        cv_scores_xgb  = cross_val_score(
            self.model_xgb, X_scaled, y, cv=tscv, scoring="accuracy", n_jobs=-1
        )
        self.model_xgb.fit(X_scaled, y)

        # Evaluate on full training set (in-sample check)
        y_pred = self._ensemble_predict_classes(X_scaled)

        report = classification_report(y, y_pred, target_names=["HOLD", "BUY", "SELL"], output_dict=True)

        self.metrics.update({
            "train_accuracy":  round(accuracy_score(y, y_pred), 4),
            "cv_accuracy":     round(np.mean(cv_scores_lgbm), 4),
            "cv_std":          round(np.std(cv_scores_lgbm), 4),
            "precision_buy":   round(report.get("BUY", {}).get("precision", 0), 4),
            "precision_sell":  round(report.get("SELL", {}).get("precision", 0), 4),
            "recall_buy":      round(report.get("BUY", {}).get("recall", 0), 4),
            "recall_sell":     round(report.get("SELL", {}).get("recall", 0), 4),
            "f1_buy":          round(report.get("BUY", {}).get("f1-score", 0), 4),
            "f1_sell":         round(report.get("SELL", {}).get("f1-score", 0), 4),
            "training_samples": len(X),
            "last_trained":    datetime.now().isoformat(),
        })

        self.is_trained    = True
        self.last_trained  = datetime.now()
        self.bars_since_retrain = 0
        self.new_data_buffer = []

        logger.info(f"Training complete | CV Acc={self.metrics['cv_accuracy']:.3f} ± {self.metrics['cv_std']:.3f}")
        logger.info(f"BUY precision={self.metrics['precision_buy']:.3f} | SELL precision={self.metrics['precision_sell']:.3f}")

        # Log performance history
        self.performance_log.append({
            "timestamp": datetime.now().isoformat(),
            "cv_accuracy": self.metrics["cv_accuracy"],
            "samples": len(X),
        })

        self._save_model()
        return self.metrics

    # ─────────────────────────────────────────
    # SIGNAL GENERATION
    # ─────────────────────────────────────────

    def generate_signal(self, df: pd.DataFrame) -> dict:
        """
        Generate a trading signal for the most recent bar.

        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": 0.0-1.0,
                "buy_prob": 0.0-1.0,
                "sell_prob": 0.0-1.0,
                "hold_prob": 0.0-1.0,
                "timestamp": ...,
                "price": ...,
                "adx": ...,
                "regime": ...,
                "reasoning": [...],
                "action_recommended": True|False,
            }
        """
        if not self.is_trained:
            return self._untrained_response()

        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            logger.error(f"Missing features: {missing}")
            return self._error_response(f"Missing features: {missing}")

        # Use latest bar — only features the model was trained on
        available = [f for f in self.feature_names if f in df.columns]
        latest = df[available].iloc[-1:]
        X      = self.scaler.transform(latest.values)

        # Get probabilities from ensemble
        probs = self._ensemble_predict_proba(X)[0]
        hold_prob, buy_prob, sell_prob = probs[0], probs[1], probs[2]

        # Determine signal
        if buy_prob >= config.BUY_THRESHOLD:
            signal     = "BUY"
            confidence = buy_prob
        elif sell_prob >= config.SELL_THRESHOLD:
            signal     = "SELL"
            confidence = sell_prob
        else:
            signal     = "HOLD"
            confidence = hold_prob

        # Get current market context
        latest_row  = df.iloc[-1]
        adx         = float(latest_row.get("adx", 0))
        adx_trend   = int(latest_row.get("adx_trend", 0))
        rsi         = float(latest_row.get("rsi", 50))
        bb_pos      = float(latest_row.get("bb_position", 0.5))
        cpr_pos     = int(latest_row.get("cpr_position", 0))

        # Build reasoning
        reasoning = self._build_reasoning(
            signal, confidence, adx, adx_trend, rsi, bb_pos, cpr_pos, latest_row
        )

        # Risk filter: suppress weak signals
        action_recommended = (
            confidence >= config.MIN_SIGNAL_CONFIDENCE and
            adx >= config.MIN_ADX_FOR_TRADE and
            signal != "HOLD"
        )

        # Regime classification
        regime = self._classify_regime(adx, latest_row)

        result = {
            "signal":               signal,
            "confidence":           round(float(confidence), 4),
            "buy_prob":             round(float(buy_prob), 4),
            "sell_prob":            round(float(sell_prob), 4),
            "hold_prob":            round(float(hold_prob), 4),
            "timestamp":            df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
            "price":                float(latest_row["close"]),
            "adx":                  round(adx, 2),
            "rsi":                  round(rsi, 2),
            "regime":               regime,
            "reasoning":            reasoning,
            "action_recommended":   action_recommended,
            "emoji":                SIGNAL_COLORS[{"BUY":1,"SELL":2,"HOLD":0}[signal]],
        }

        # Store for online learning feedback
        self.signal_history.append(result.copy())
        self.bars_since_retrain += 1

        return result

    def generate_signals_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals for entire DataFrame (for backtesting)."""
        if not self.is_trained:
            return df

        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            return df

        X = self.scaler.transform(df[self.feature_names].values)
        probs = self._ensemble_predict_proba(X)

        df = df.copy()
        df["hold_prob"] = probs[:, 0]
        df["buy_prob"]  = probs[:, 1]
        df["sell_prob"] = probs[:, 2]

        df["signal"] = "HOLD"
        df.loc[df["buy_prob"]  >= config.BUY_THRESHOLD,  "signal"] = "BUY"
        df.loc[df["sell_prob"] >= config.SELL_THRESHOLD, "signal"] = "SELL"
        df["confidence"] = df[["hold_prob", "buy_prob", "sell_prob"]].max(axis=1)

        return df

    # ─────────────────────────────────────────
    # ONLINE / CONTINUOUS LEARNING
    # ─────────────────────────────────────────

    def add_new_data(self, df: pd.DataFrame):
        """
        Add new market data to the learning buffer.
        Called periodically (e.g., every 30 minutes with latest candles).
        The model will retrain when buffer is large enough.
        """
        self.new_data_buffer.append(df)
        logger.info(f"Added {len(df)} bars to learning buffer | total={sum(len(d) for d in self.new_data_buffer)}")

    def maybe_retrain(self, full_df: pd.DataFrame) -> bool:
        """
        Check if retraining conditions are met and retrain if so.
        Call this periodically (e.g., every hour or at end of day).

        Returns True if retrain happened.
        """
        if self._should_retrain():
            logger.info("Retraining triggered...")
            self.train(full_df, force=True)
            return True
        return False

    def record_outcome(self, signal: dict, actual_outcome: str):
        """
        Record whether a signal was correct.
        actual_outcome: "BUY_CORRECT", "SELL_CORRECT", "WRONG", "NEUTRAL"
        Used to calculate rolling accuracy.
        """
        correct = (
            (signal["signal"] == "BUY"  and actual_outcome == "BUY_CORRECT") or
            (signal["signal"] == "SELL" and actual_outcome == "SELL_CORRECT")
        )
        self.metrics["total_signals"] += 1
        if correct:
            self.metrics["correct_signals"] += 1

        rolling_window = 50
        self.metrics["rolling_accuracy"].append(1 if correct else 0)
        if len(self.metrics["rolling_accuracy"]) > rolling_window:
            self.metrics["rolling_accuracy"].pop(0)

        rolling_acc = np.mean(self.metrics["rolling_accuracy"])
        logger.info(f"Outcome recorded | rolling_accuracy={rolling_acc:.3f} ({self.metrics['total_signals']} signals)")

    # ─────────────────────────────────────────
    # FEATURE IMPORTANCE
    # ─────────────────────────────────────────

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Return top N most important features."""
        if not self.is_trained:
            return pd.DataFrame()

        importance = self.model_lgbm.feature_importances_
        fi = pd.DataFrame({
            "feature":    self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False).head(top_n)

        return fi

    def get_performance_summary(self) -> dict:
        """Full performance summary for dashboard display."""
        rolling_acc = np.mean(self.metrics["rolling_accuracy"]) if self.metrics["rolling_accuracy"] else 0
        return {
            **self.metrics,
            "rolling_accuracy_value": round(rolling_acc, 4),
            "is_trained": self.is_trained,
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "bars_since_retrain": self.bars_since_retrain,
            "model_type": config.MODEL_TYPE,
            "total_signals": len(self.signal_history),
            "performance_trend": self.performance_log[-10:],
        }

    # ─────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────

    def _ensemble_predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Average probabilities from LightGBM and XGBoost."""
        probs_lgbm = self.model_lgbm.predict_proba(X)
        probs_xgb  = self.model_xgb.predict_proba(X)
        return (probs_lgbm + probs_xgb) / 2

    def _ensemble_predict_classes(self, X: np.ndarray) -> np.ndarray:
        probs = self._ensemble_predict_proba(X)
        return np.argmax(probs, axis=1)

    def _should_retrain(self) -> bool:
        """Check if retraining is due."""
        if not self.is_trained:
            return True
        if self.bars_since_retrain >= config.RETRAIN_AFTER_BARS:
            return True
        if self.last_trained is None:
            return True
        # Daily retrain after market close
        if config.RETRAIN_INTERVAL == "daily":
            return datetime.now().date() > self.last_trained.date()
        # Hourly retrain
        if config.RETRAIN_INTERVAL == "hourly":
            return (datetime.now() - self.last_trained).seconds > 3600
        return False

    def _classify_regime(self, adx: float, row: pd.Series) -> str:
        """Classify current market regime."""
        trending_up   = row.get("trending_up", 0)
        trending_down = row.get("trending_down", 0)
        ranging       = row.get("ranging", 0)

        if trending_up:
            return "TRENDING_UP"
        elif trending_down:
            return "TRENDING_DOWN"
        elif adx < 20:
            return "RANGING"
        elif ranging:
            return "LOW_VOLATILITY"
        else:
            return "TRANSITIONING"

    def _build_reasoning(self, signal, confidence, adx, adx_trend, rsi, bb_pos, cpr_pos, row) -> list:
        """Human-readable reasoning for why this signal was generated."""
        reasons = []

        if adx >= 25:
            reasons.append(f"ADX={adx:.1f} — Strong trend present")
        elif adx >= 20:
            reasons.append(f"ADX={adx:.1f} — Moderate trend")
        else:
            reasons.append(f"ADX={adx:.1f} — Weak/no trend (lower confidence)")

        if rsi > 70:
            reasons.append(f"RSI={rsi:.1f} — Overbought territory")
        elif rsi < 30:
            reasons.append(f"RSI={rsi:.1f} — Oversold territory")
        else:
            reasons.append(f"RSI={rsi:.1f} — Neutral zone")

        if bb_pos > 0.8:
            reasons.append("Price near Upper Bollinger Band — potential resistance")
        elif bb_pos < 0.2:
            reasons.append("Price near Lower Bollinger Band — potential support")

        cpr_map = {1: "Above CPR — bullish bias", -1: "Below CPR — bearish bias", 0: "Inside CPR — consolidation"}
        reasons.append(cpr_map.get(cpr_pos, "CPR position unknown"))

        macd_hist = row.get("macd_hist", 0)
        if macd_hist > 0:
            reasons.append(f"MACD histogram positive ({macd_hist:.2f}) — bullish momentum")
        else:
            reasons.append(f"MACD histogram negative ({macd_hist:.2f}) — bearish momentum")

        if confidence >= 0.75:
            reasons.append(f"High confidence signal ({confidence:.1%})")
        elif confidence >= 0.62:
            reasons.append(f"Moderate confidence ({confidence:.1%})")

        return reasons

    def _untrained_response(self) -> dict:
        return {
            "signal": "HOLD", "confidence": 0, "buy_prob": 0, "sell_prob": 0, "hold_prob": 1,
            "timestamp": datetime.now().isoformat(), "price": 0, "adx": 0, "rsi": 0,
            "regime": "UNKNOWN", "reasoning": ["Model not trained yet"],
            "action_recommended": False, "emoji": "⚪",
        }

    def _error_response(self, msg: str) -> dict:
        return {**self._untrained_response(), "reasoning": [f"Error: {msg}"]}

    # ─────────────────────────────────────────
    # MODEL PERSISTENCE
    # ─────────────────────────────────────────

    def _save_model(self):
        """Save trained model to disk."""
        try:
            joblib.dump(self.model_lgbm, f"{config.MODEL_DIR}/model_lgbm.pkl")
            joblib.dump(self.model_xgb,  f"{config.MODEL_DIR}/model_xgb.pkl")
            joblib.dump(self.scaler,     f"{config.MODEL_DIR}/scaler.pkl")

            meta = {
                "last_trained":  self.last_trained.isoformat() if self.last_trained else None,
                "metrics":       {k: v for k, v in self.metrics.items() if k != "rolling_accuracy"},
                "feature_names": self.feature_names,
                "performance_log": self.performance_log,
            }
            with open(f"{config.MODEL_DIR}/meta.json", "w") as f:
                json.dump(meta, f, indent=2)

            logger.info("Model saved to disk")
        except Exception as e:
            logger.error(f"Model save failed: {e}")

    def _try_load_saved_model(self):
        """Load previously saved model on startup."""
        try:
            lgbm_path = f"{config.MODEL_DIR}/model_lgbm.pkl"
            xgb_path  = f"{config.MODEL_DIR}/model_xgb.pkl"
            if os.path.exists(lgbm_path) and os.path.exists(xgb_path):
                self.model_lgbm  = joblib.load(lgbm_path)
                self.model_xgb   = joblib.load(f"{config.MODEL_DIR}/model_xgb.pkl")
                self.scaler      = joblib.load(f"{config.MODEL_DIR}/scaler.pkl")
                self.is_trained  = True

                with open(f"{config.MODEL_DIR}/meta.json") as f:
                    meta = json.load(f)
                self.last_trained   = datetime.fromisoformat(meta["last_trained"]) if meta.get("last_trained") else None
                self.metrics.update(meta.get("metrics", {}))
                self.performance_log = meta.get("performance_log", [])

                logger.info(f"Loaded saved model | last_trained={self.last_trained}")
        except Exception as e:
            logger.info(f"No saved model found, will train fresh: {e}")
