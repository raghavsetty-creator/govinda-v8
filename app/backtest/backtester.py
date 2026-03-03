"""
GOVINDA NIFTY AI — Backtester v2
==================================
Shows EXACT per-trade breakdown:
  Points gained × ₹65 (1 lot) - all charges = Net Profit

NSE Charges (NIFTY Options, 1 lot):
  Brokerage:        ₹20 × 2 legs          = ₹40.00
  STT:              0.1% × sell premium    ≈ ₹16.25  (ATM ~₹250 premium)
  Exchange (NSE):   0.053% × both sides   ≈ ₹0.27
  GST (18%):        on brokerage+exchange  ≈ ₹7.25
  SEBI:             ₹10 per crore          ≈ ₹0.03
  Stamp Duty:       0.003% on buy side     ≈ ₹0.49
  ─────────────────────────────────────────────────
  TOTAL per lot round trip                ≈ ₹64.29
"""

import pandas as pd
import numpy as np
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

LOT_SIZE = 65  # NIFTY Jan 2026

def nse_charges(index_price: float, lots: int = 1) -> dict:
    """
    Calculate exact NSE charges for NIFTY options.
    Uses ATM premium = ~1% of index as approximation.
    Returns full breakdown + total.
    """
    # Approximate ATM premium (weekly ~0.8%, monthly ~1.5%)
    premium_per_unit = index_price * 0.010    # 1% of index ≈ ATM premium
    total_premium    = premium_per_unit * LOT_SIZE * lots

    brokerage        = 20 * 2 * lots                           # ₹20 per leg per lot
    stt              = 0.001  * total_premium                  # 0.1% on sell side
    exchange         = 0.00053 * total_premium * 2             # both legs
    gst              = 0.18   * (brokerage + exchange)         # 18% on bro+exchange
    sebi             = 0.000001 * total_premium * 2            # ₹10/crore
    stamp            = 0.00003  * (total_premium / 2)          # 0.003% on buy side

    total = brokerage + stt + exchange + gst + sebi + stamp

    return {
        "brokerage":   round(brokerage, 2),
        "stt":         round(stt, 2),
        "exchange":    round(exchange, 2),
        "gst":         round(gst, 2),
        "sebi":        round(sebi, 2),
        "stamp":       round(stamp, 2),
        "total":       round(total, 2),
    }


def suggest_expiry(adx: float, mtf_score: float, days_to_monthly: int) -> str:
    """
    Suggest weekly vs monthly based on trend strength.
    Strong trend (ADX>30, all MTF aligned) → monthly gives more time for move.
    Weak/moderate trend → weekly for quick scalp.
    """
    if adx >= 30 and mtf_score >= 3:
        return "MONTHLY"   # Strong trend — buy time with monthly
    elif adx >= 25:
        return "WEEKLY"    # Moderate trend — standard weekly
    else:
        return "WEEKLY"    # Weak — only weekly, tighter expiry


class Backtester:
    """
    Backtester showing exact per-trade P&L:

    Net P&L per lot = (Points × ₹65) - Total NSE Charges

    Example:
      NIFTY moves 100 points SHORT
      Gross = 100 × 65 = ₹6,500
      Charges = ₹64
      Net = ₹6,436
    """

    def __init__(self, initial_capital: float = 500000):
        self.initial_capital = initial_capital
        self.lot_size        = LOT_SIZE
        self.slippage_pct    = 0.0002    # 0.02% realistic slippage
        self.risk_per_trade  = 0.01      # 1% capital risk per trade
        self.default_sl_pts  = 50        # 50 points default stop loss

    def _calc_lots(self, capital: float) -> int:
        """
        Risk-based lot sizing.
        Risk ₹ = capital × 1%
        Risk per lot = SL_points × lot_size = 50 × 65 = ₹3,250
        Lots = Risk ₹ / Risk per lot
        """
        risk_amount  = capital * self.risk_per_trade     # e.g. ₹5,000 on ₹5L
        risk_per_lot = self.default_sl_pts * self.lot_size  # 50 × 65 = ₹3,250
        lots = max(1, int(risk_amount / risk_per_lot))
        return min(lots, 5)  # cap 5 lots

    def run(self, df: pd.DataFrame) -> dict:
        if "signal" not in df.columns:
            return {"error": "No signal column"}

        df       = df.copy()
        capital  = self.initial_capital
        trades   = []
        position = None
        equity_curve = [capital]

        for i in range(1, len(df)):
            row  = df.iloc[i]
            prev = df.iloc[i - 1]
            signal     = prev["signal"]
            entry_open = row["open"]

            # ── ENTRY ──────────────────────────────
            if position is None and signal in ["BUY", "SELL"]:
                slip        = entry_open * self.slippage_pct
                entry_price = entry_open + slip if signal == "BUY" else entry_open - slip
                lots        = self._calc_lots(capital)
                adx_val     = float(prev.get("adx", 20))
                mtf_score   = 2  # default — real MTF score from engine
                expiry_type = suggest_expiry(adx_val, mtf_score, 14)

                position = {
                    "side":         "LONG"  if signal == "BUY" else "SHORT",
                    "entry_price":  entry_price,
                    "entry_time":   row.name,
                    "lots":         lots,
                    "adx":          adx_val,
                    "expiry_type":  expiry_type,
                }

            # ── EXIT ───────────────────────────────
            elif position:
                should_exit = (
                    (position["side"] == "LONG"  and signal == "SELL") or
                    (position["side"] == "SHORT" and signal == "BUY")  or
                    (i == len(df) - 1)
                )

                if should_exit:
                    exit_price = row["close"]
                    lots       = position["lots"]

                    # Points moved (index level)
                    if position["side"] == "LONG":
                        points = exit_price - position["entry_price"]
                    else:
                        points = position["entry_price"] - exit_price

                    # Gross P&L: points × ₹65 per unit × lots
                    gross_pnl_1lot = points * self.lot_size
                    gross_pnl_all  = gross_pnl_1lot * lots

                    # NSE charges
                    charges_1lot = nse_charges(position["entry_price"], lots=1)
                    charges_all  = nse_charges(position["entry_price"], lots=lots)

                    # Net P&L
                    net_pnl_1lot = gross_pnl_1lot - charges_1lot["total"]
                    net_pnl_all  = gross_pnl_all  - charges_all["total"]

                    capital += net_pnl_all
                    equity_curve.append(capital)

                    trades.append({
                        # ── Trade info ──
                        "entry_time":       position["entry_time"],
                        "exit_time":        row.name,
                        "side":             position["side"],
                        "expiry_type":      position["expiry_type"],
                        "adx_at_entry":     round(position["adx"], 1),
                        # ── Prices ──
                        "entry_price":      round(position["entry_price"], 2),
                        "exit_price":       round(exit_price, 2),
                        "points":           round(points, 2),
                        # ── Per 1 lot breakdown ──
                        "gross_1lot":       round(gross_pnl_1lot, 2),
                        "charges_1lot":     charges_1lot["total"],
                        "brokerage_1lot":   charges_1lot["brokerage"],
                        "stt_1lot":         charges_1lot["stt"],
                        "gst_1lot":         charges_1lot["gst"],
                        "net_1lot":         round(net_pnl_1lot, 2),
                        # ── Actual trade (all lots) ──
                        "lots":             lots,
                        "gross_all":        round(gross_pnl_all, 2),
                        "charges_all":      charges_all["total"],
                        "net_pnl_all":      round(net_pnl_all, 2),
                        "pnl_pct":          round((net_pnl_all / capital) * 100, 3),
                        # ── Running capital ──
                        "capital":          round(capital, 2),
                        "result":           "WIN" if net_pnl_all > 0 else "LOSS",
                    })
                    position = None
                else:
                    equity_curve.append(capital)

        return self._compile_results(trades, equity_curve)

    def _compile_results(self, trades, equity_curve):
        if not trades:
            return {"error": "No trades generated"}

        df_t  = pd.DataFrame(trades)
        wins  = df_t[df_t["result"] == "WIN"]
        loss  = df_t[df_t["result"] == "LOSS"]

        total_return = (equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        returns      = df_t["pnl_pct"].values / 100
        sharpe       = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252) if len(returns) > 1 else 0
        eq           = pd.Series(equity_curve)
        max_dd       = ((eq - eq.cummax()) / eq.cummax() * 100).min()

        return {
            "total_trades":       len(trades),
            "wins":               len(wins),
            "losses":             len(loss),
            "win_rate":           round(len(wins) / len(trades) * 100, 2),
            "avg_win_rs":         round(wins["net_pnl_all"].mean(), 2) if len(wins) else 0,
            "avg_loss_rs":        round(loss["net_pnl_all"].mean(), 2) if len(loss) else 0,
            "avg_win_1lot":       round(wins["net_1lot"].mean(), 2) if len(wins) else 0,
            "avg_loss_1lot":      round(loss["net_1lot"].mean(), 2) if len(loss) else 0,
            "total_charges":      round(df_t["charges_all"].sum(), 2),
            "total_gross":        round(df_t["gross_all"].sum(), 2),
            "total_pnl_rs":       round(df_t["net_pnl_all"].sum(), 2),
            "profit_factor":      round(wins["net_pnl_all"].sum() / abs(loss["net_pnl_all"].sum() + 1e-9), 2),
            "total_return_pct":   round(total_return, 2),
            "final_capital":      round(equity_curve[-1], 2),
            "sharpe_ratio":       round(sharpe, 3),
            "max_drawdown_pct":   round(max_dd, 2),
            "equity_curve":       equity_curve,
            "trades":             df_t.to_dict("records"),
        }
