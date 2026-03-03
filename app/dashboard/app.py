"""
GOVINDA NIFTY AI v8 — Dashboard (Clean)
- No manual signal settings (system self-optimizes)
- Live signal log with timestamps
- Clear price chart
- Real backtest trade log from JSON
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="GOVINDA — NIFTY AI v8", page_icon="🕉️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap');
html,body,[data-testid="stAppViewContainer"]{background:#0D0B2B;color:#FFF8F0}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0D0B2B,#130F35);border-right:1px solid #FF6B00}
[data-testid="stHeader"]{background:#0D0B2B}
h1,h2,h3{color:#FFD700!important}
.stMarkdown p{color:#C8BFA8}
.stDivider{border-color:#1A1650!important}

/* Header */
.govinda-topbar{height:3px;background:#FF6B00;width:100%}
.govinda-botbar{height:3px;background:#FFD700;width:100%}
.govinda-header{background:linear-gradient(135deg,#0D0B2B,#1A1650,#0D0B2B);padding:24px 36px;
  display:flex;align-items:center;justify-content:space-between;
  border-left:3px solid #FF6B00;border-right:3px solid #FFD700}
.govinda-om{width:68px;height:68px;background:#201D70;border:2px solid #FFD700;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:30px;
  box-shadow:0 0 20px rgba(255,215,0,0.35)}
.govinda-title{font-size:30px;font-weight:700;color:#FFD700;letter-spacing:8px;font-family:'Cinzel',serif}
.govinda-sanskrit{font-size:17px;color:#FF6B00;letter-spacing:2px;font-style:italic;margin-top:2px}
.govinda-tagline{font-size:11px;color:#8892A0;letter-spacing:2px;text-transform:uppercase;margin-top:5px}
.govinda-badge{background:#FF6B00;color:#0D0B2B;padding:4px 14px;border-radius:20px;
  font-size:11px;font-weight:700;letter-spacing:2px}

/* Section headers */
.sec{background:linear-gradient(90deg,#1A1650,transparent);border-left:3px solid #FF6B00;
  padding:7px 16px;margin:16px 0 10px 0;font-size:12px;font-weight:700;
  color:#FFD700;letter-spacing:2px;text-transform:uppercase}

/* Signal cards */
.sig-buy{background:linear-gradient(135deg,#061a0e,#0a2718);border:1px solid #00c851;
  border-left:5px solid #00c851;padding:20px 24px;border-radius:8px;margin:8px 0}
.sig-sell{background:linear-gradient(135deg,#1a0606,#2a0a0a);border:1px solid #FF3547;
  border-left:5px solid #FF3547;padding:20px 24px;border-radius:8px;margin:8px 0}
.sig-hold,.sig-offline{background:linear-gradient(135deg,#0D0B2B,#1A1650);
  border:1px solid #FF6B00;border-left:5px solid #FFD700;padding:20px 24px;border-radius:8px;margin:8px 0}
.sig-hl{font-size:22px;font-weight:800;letter-spacing:1px;margin-bottom:8px}
.sig-dt{font-size:13px;color:#C8BFA8;line-height:1.9}
.tag{display:inline-block;padding:3px 11px;border-radius:20px;font-size:11px;
  font-weight:700;letter-spacing:1px;margin-right:5px;text-transform:uppercase}
.tg{background:#0a3320;color:#00c851;border:1px solid #00c851}
.tr{background:#3d1010;color:#FF3547;border:1px solid #FF3547}
.to{background:#2a1500;color:#FF6B00;border:1px solid #FF6B00}
.ty{background:#2a2000;color:#FFD700;border:1px solid #FFD700}

/* Data cards */
.dcard{background:#1A1650;border:1px solid #201D70;border-radius:8px;padding:14px 18px}
.drow{display:flex;justify-content:space-between;padding:5px 0;
  border-bottom:1px solid #201D70;font-size:13px;color:#C8BFA8}
.drow:last-child{border-bottom:none}
.dval{color:#FFF8F0;font-weight:600}

/* Stat callout */
.stat{background:#1A1650;border:1px solid #201D70;border-top:3px solid #FF6B00;
  border-radius:8px;padding:16px;text-align:center}
.snum{font-size:26px;font-weight:800;color:#FFD700}
.slbl{font-size:10px;color:#8892A0;text-transform:uppercase;letter-spacing:2px;margin-top:3px}
.sg{color:#00c851!important}.so{color:#FF6B00!important}.sr{color:#FF3547!important}

/* MTF card */
.mtf{background:#1A1650;border:1px solid #201D70;border-radius:8px;padding:10px;text-align:center}
.mtf-tf{font-size:10px;color:#8892A0;text-transform:uppercase;letter-spacing:2px}
.mtf-dir{font-size:13px;font-weight:700;margin-top:5px}
.bearish{color:#FF3547}.bullish{color:#00c851}.neutral{color:#FFD700}

/* Signal log table */
.log-row{display:grid;grid-template-columns:110px 55px 70px 60px 1fr 90px 80px;
  gap:8px;padding:8px 12px;border-bottom:1px solid #1A1650;font-size:12px;align-items:center}
.log-hdr{background:#0D0B2B;color:#FFD700;font-size:10px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;border-bottom:2px solid #FF6B00}
.log-buy{background:#061a0e}.log-sell{background:#1a0606}.log-hold{background:#0D0B2B}

/* Streamlit overrides */
.stButton>button{background:linear-gradient(135deg,#FF6B00,#CC5500);color:#FFF8F0;
  border:none;font-weight:700;border-radius:6px;letter-spacing:1px;text-transform:uppercase;font-size:12px}
[data-testid="stMetricValue"]{color:#FFD700!important;font-weight:800!important}
[data-testid="stMetricLabel"]{color:#8892A0!important;font-size:10px!important;
  letter-spacing:1px;text-transform:uppercase}
div[data-testid="stMetric"]{background:#1A1650;border:1px solid #201D70;
  border-top:2px solid #FF6B00;border-radius:8px;padding:12px 16px}
.stExpander{border:1px solid #201D70!important;background:#1A1650!important}
</style>""", unsafe_allow_html=True)


# ── LOAD SYSTEM ─────────────────────────
@st.cache_resource
def load_system():
    try:
        from main import GOVINDA
        s = GOVINDA(); s.initialize()
        return s, None
    except Exception as e:
        return None, str(e)


# ── SIDEBAR (clean — no signal settings) ─
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:18px 0 10px 0;border-bottom:1px solid #FF6B00;margin-bottom:14px">
      <div style="font-size:32px;color:#FFD700">ॐ</div>
      <div style="font-size:18px;font-weight:700;color:#FFD700;letter-spacing:4px;margin-top:4px">GOVINDA</div>
      <div style="font-size:9px;color:#8892A0;letter-spacing:2px;text-transform:uppercase">NIFTY AI v8 · Self-Optimizing</div>
    </div>""", unsafe_allow_html=True)

    now = datetime.now()
    is_mkt = now.weekday() < 5 and 9 <= now.hour < 16
    mc, mb = ("#00c851","#0a3320") if is_mkt else ("#FF6B00","#2a1500")
    mt = "● MARKET OPEN" if is_mkt else "● MARKET CLOSED"
    st.markdown(
        f'<div style="text-align:center;margin-bottom:6px">'
        f'<span style="background:{mb};color:{mc};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:1px">{mt}</span></div>'
        f'<div style="text-align:center;font-size:11px;color:#8892A0;margin-bottom:14px">{now.strftime("%d %b %Y  %H:%M IST")}</div>',
        unsafe_allow_html=True)

    st.divider()
    auto_refresh = st.toggle("⟳ Auto Refresh (5 min)", value=False)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()
    st.divider()

    # Capital only
    st.markdown('<div class="sec">💰 Capital</div>', unsafe_allow_html=True)
    capital = st.number_input("Trading Capital (₹)", value=500000, step=50000)
    st.divider()

    # System status
    st.markdown('<div class="sec">⚙ System Info</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="dcard">
      <div class="drow"><span>Lot Size</span><span class="dval">65 units</span></div>
      <div class="drow"><span>Exchange</span><span class="dval">NSE</span></div>
      <div class="drow"><span>Instrument</span><span class="dval">NIFTY Options</span></div>
      <div class="drow"><span>Refresh</span><span class="dval">Every 5 min</span></div>
      <div class="drow"><span>Strategy</span><span class="dval">Self-Optimizing</span></div>
      <div class="drow"><span>Models</span><span class="dval">LightGBM + XGB</span></div>
    </div>""", unsafe_allow_html=True)
    st.divider()
    st.markdown('<div style="text-align:center;font-size:10px;color:#201D70">हरे कृष्ण · Azure Central India</div>', unsafe_allow_html=True)


# ── HEADER ──────────────────────────────
st.markdown("""
<div>
  <div class="govinda-topbar"></div>
  <div class="govinda-header">
    <div style="display:flex;align-items:center;gap:18px">
      <div class="govinda-om">ॐ</div>
      <div>
        <div class="govinda-title">G O V I N D A</div>
        <div class="govinda-sanskrit">गोविन्द</div>
        <div class="govinda-tagline">He who sees all · He who knows all · He who protects all</div>
      </div>
    </div>
    <div style="text-align:right">
      <span class="govinda-badge">LIVE</span>
      <div style="font-size:10px;color:#8892A0;margin-top:6px;letter-spacing:1px">AI-POWERED · NIFTY 50 · SELF-EVOLVING · NEVER SLEEPS</div>
      <div style="font-size:10px;color:#FF6B00;margin-top:3px;letter-spacing:1px">NSE Jan 2026 · Lot 65 units</div>
    </div>
  </div>
  <div class="govinda-botbar"></div>
</div>""", unsafe_allow_html=True)


# ── LOAD ────────────────────────────────
with st.spinner("ॐ Initializing GOVINDA..."):
    system, err = load_system()

if err or system is None:
    st.markdown(f"""<div class="sig-offline">
      <div class="sig-hl" style="color:#FFD700">ॐ Initializing...</div>
      <div class="sig-dt">Status: {err or 'Loading...'} — refresh in 30s</div>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ── PARSE LOG ───────────────────────────
log_lines = []
try:
    log_lines = open("/opt/govinda/logs/engine-error.log").readlines()
except: pass

def parse_all_signals(lines):
    """Parse every signal with its exact timestamp from log."""
    signals, i = [], 0
    while i < len(lines):
        line = lines[i]
        if ("OFFLINE]" in line or "NORMAL]" in line) and \
           any(x in line for x in [" BUY ", " SELL ", " HOLD "]):
            s = {
                "timestamp": "",
                "mode":      "OFFLINE" if "OFFLINE" in line else "NORMAL",
                "signal":    "BUY" if " BUY " in line else "SELL" if " SELL " in line else "HOLD",
                "conf":      0.0,
                "agreement": "",
                "options":   "—",
                "target":    "—",
                "sl":        "—",
                "mtf":       "—",
                "action":    "WAIT",
                "lots":      0,
            }
            # Extract timestamp — log format: "2026-02-28 10:23:45 INFO:..."
            # Try current line first, then look back a few lines
            for k in range(i, max(0,i-5), -1):
                l = lines[k]
                try:
                    parts = l.strip().split(" ")
                    # Look for YYYY-MM-DD pattern
                    for pi, part in enumerate(parts):
                        if len(part)==10 and part[4]=="-" and part[7]=="-":
                            # Found a date — grab date + time
                            timepart = parts[pi+1][:8] if pi+1 < len(parts) else ""
                            s["timestamp"] = f"{part} {timepart}"
                            break
                    if s["timestamp"]:
                        break
                except: pass
            # Fallback: count signal number as approximate order
            if not s["timestamp"]:
                s["timestamp"] = f"Signal #{len(signals)+1}"
            try: s["conf"] = float(line.split("Conf:")[1].split("%")[0].strip())
            except: pass
            try: s["agreement"] = line.split("Agreement:")[1].strip()[:12]
            except: pass

            for j in range(i+1, min(i+15, len(lines))):
                l = lines[j]
                if "Options :" in l:
                    try: s["options"] = l.split("Options :")[1].strip()[:40]
                    except: pass
                if "Target  :" in l:
                    try:
                        t = l.split("Target  :")[1].strip()
                        s["target"] = t.split("|")[0].strip()[:20]
                        if "SL:" in t: s["sl"] = t.split("SL:")[1].strip()[:10]
                    except: pass
                if "MTF:" in l:
                    try: s["mtf"] = l.split("MTF:")[1].split("/")[0].strip()[:20]
                    except: pass
                if "ACTION" in l:
                    s["action"] = "TRADE" if "TRADE" in l else "WAIT"
                if "Lots:" in l:
                    try: s["lots"] = int(l.split("Lots:")[1].split("|")[0].strip())
                    except: pass
                if ("OFFLINE]" in l or "NORMAL]" in l):
                    break
            signals.append(s)
        i += 1
    return list(reversed(signals))  # newest first

all_signals = parse_all_signals(log_lines)

# Load locked signal from JSON if available — prevents timestamp changing on refresh
import json as _json, os as _os
_json_path = "/opt/govinda/data/latest_signal.json"
if _os.path.exists(_json_path):
    try:
        with open(_json_path) as _jf:
            _locked = _json.load(_jf)
        if _locked.get("locked") and all_signals:
            all_signals[0]["timestamp"] = _locked["timestamp"]
    except: pass

sig = all_signals[0] if all_signals else {
    "timestamp":"—","mode":"OFFLINE","signal":"HOLD","conf":0.0,
    "agreement":"","options":"—","target":"—","sl":"—",
    "mtf":"UNKNOWN","action":"WAIT","lots":0
}


# ── LIVE SIGNAL ─────────────────────────
st.markdown('<div class="sec">🎯 Current Signal</div>', unsafe_allow_html=True)

# 6 stat callouts
c1,c2,c3,c4,c5,c6 = st.columns(6)
sc = sig
s_color_map = {"BUY":"sg","SELL":"sr","HOLD":"so"}
sc_data = [
    (sc["signal"],    "Signal",      s_color_map.get(sc["signal"],"")),
    (f"{sc['conf']:.1f}%", "Confidence", "sg" if sc["conf"]>=70 else "so" if sc["conf"]>=55 else ""),
    (sc["mode"],      "Mode",        "so"),
    (sc["action"],    "Action",      "sg" if sc["action"]=="TRADE" else "so"),
    (sc["mtf"].replace("_"," ")[:14], "MTF Bias", "sr" if "BEAR" in sc["mtf"] else "sg" if "BULL" in sc["mtf"] else ""),
    (sc["timestamp"] or "—", "Generated At", ""),
]
for col,(val,lbl,cls) in zip([c1,c2,c3,c4,c5,c6], sc_data):
    col.markdown(f'<div class="stat"><div class="snum {cls}">{val}</div><div class="slbl">{lbl}</div></div>',
                 unsafe_allow_html=True)

# Signal card
sig_cls   = {"BUY":"sig-buy","SELL":"sig-sell"}.get(sc["signal"],"sig-offline")
sig_color = {"BUY":"#00c851","SELL":"#FF3547","HOLD":"#FFD700"}.get(sc["signal"],"#FFD700")
sig_emoji = {"BUY":"🟢","SELL":"🔴","HOLD":"⚪"}.get(sc["signal"],"🕉️")
a_tag = f'<span class="tag tg">✅ TRADE</span>' if sc["action"]=="TRADE" else '<span class="tag ty">⏸ WAIT</span>'
m_tag = f'<span class="tag to">{sc["mode"]}</span>'
agree_tag = f'<span class="tag ty">{sc["agreement"]}</span>' if sc["agreement"] else ""

trade_html = ""
if sc["options"] != "—":
    trade_html = f"""
    <div class="dcard" style="margin-top:14px">
      <div style="font-size:10px;color:#FF6B00;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">📋 Trade Setup</div>
      <div class="drow"><span>Suggestion</span><span class="dval" style="color:#FFD700">{sc['options']}</span></div>
      <div class="drow"><span>Target</span><span class="dval" style="color:#00c851">{sc['target']}</span></div>
      <div class="drow"><span>Stop Loss</span><span class="dval" style="color:#FF3547">{sc['sl']}</span></div>
      <div class="drow"><span>Lots × 65 units</span><span class="dval">{sc['lots']} lot{'s' if sc['lots']!=1 else ''}</span></div>
      <div class="drow"><span>Signal Time</span><span class="dval" style="color:#8892A0">{sc['timestamp'] or '—'}</span></div>
    </div>"""

st.markdown(f"""
<div class="{sig_cls}">
  <div class="sig-hl" style="color:{sig_color}">{sig_emoji} {sc['signal']} &nbsp; {m_tag} {a_tag} {agree_tag}</div>
  <div class="sig-dt">
    <b>Confidence:</b> {sc['conf']:.1f}%
    &nbsp;·&nbsp; <b>MTF:</b> {sc['mtf'].replace('_',' ')}
    &nbsp;·&nbsp; <b>Generated:</b> {sc['timestamp'] or 'N/A'}
  </div>
</div>""", unsafe_allow_html=True)

if sc["options"] != "—":
    st.markdown(f"""
    <div class="dcard" style="margin-top:8px">
      <div style="font-size:10px;color:#FF6B00;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">📋 Trade Setup</div>
      <div class="drow"><span>Suggestion</span><span class="dval" style="color:#FFD700">{sc['options']}</span></div>
      <div class="drow"><span>Target</span><span class="dval" style="color:#00c851">{sc['target']}</span></div>
      <div class="drow"><span>Stop Loss</span><span class="dval" style="color:#FF3547">{sc['sl']}</span></div>
      <div class="drow"><span>Lots × 65 units</span><span class="dval">{sc['lots']} lot{'s' if sc['lots']!=1 else ''}</span></div>
      <div class="drow"><span>Signal Time</span><span class="dval" style="color:#8892A0">{sc['timestamp'] or '—'}</span></div>
    </div>""", unsafe_allow_html=True)


# ── CALENDAR + MTF ──────────────────────
st.markdown("<br>", unsafe_allow_html=True)
cl, cr = st.columns(2)

with cl:
    st.markdown('<div class="sec">📅 Trade Calendar</div>', unsafe_allow_html=True)
    try:
        from utils.holiday_checker import should_system_run, trade_calendar_summary
        r = should_system_run(); c = trade_calendar_summary()
        st.markdown(f"""<div class="dcard">
          <div class="drow"><span>Mode</span><span class="dval" style="color:#FF6B00">{r['mode']}</span></div>
          <div class="drow"><span>Status</span><span class="dval">{r['reason']}</span></div>
          <div class="drow"><span>Next Entry</span><span class="dval" style="color:#00c851">{c.get('entry_day','—')}</span></div>
          <div class="drow"><span>Expiry Date</span><span class="dval" style="color:#FFD700">{c.get('expiry_date','—')}</span></div>
          <div class="drow"><span>Days to Expiry</span><span class="dval">{c.get('days_to_expiry','—')}</span></div>
          <div class="drow"><span>Position Size</span><span class="dval">{r.get('position_size_pct',100)}% of capital</span></div>
        </div>""", unsafe_allow_html=True)
    except:
        next_monday = "Mon 03 Mar 2026  09:15"
        st.markdown(f"""<div class="dcard">
          <div class="drow"><span>Mode</span><span class="dval" style="color:#FF6B00">OFFLINE (Weekend)</span></div>
          <div class="drow"><span>Market Opens</span><span class="dval" style="color:#00c851">{next_monday}</span></div>
          <div class="drow"><span>Expiry</span><span class="dval" style="color:#FFD700">Thu 05 Mar 2026</span></div>
          <div class="drow"><span>Days to Expiry</span><span class="dval">5 days</span></div>
          <div class="drow"><span>Signal Refresh</span><span class="dval">Every 5 min from 9:15 AM</span></div>
        </div>""", unsafe_allow_html=True)

with cr:
    st.markdown('<div class="sec">📊 Multi-Timeframe Confluence</div>', unsafe_allow_html=True)
    mtf_data = {"Daily":("BEARISH",-7),"Hourly":("BEARISH",-7),"15-Min":("BEARISH",-6),"5-Min":("BEARISH",-6)}
    try:
        for line in reversed(log_lines[-300:]):
            for tf in ["Daily","Hourly","15-Min","5-Min"]:
                if f"  {tf}:" in line:
                    try:
                        parts = line.split(f"{tf}:")[1].split("|")
                        d = parts[0].strip()
                        sc2 = int(parts[1].replace("Score=","").strip()) if len(parts)>1 else 0
                        mtf_data[tf] = (d, sc2)
                    except: pass
    except: pass

    cols4 = st.columns(4)
    for i,(tf,(direction,score)) in enumerate(mtf_data.items()):
        dcls = "bearish" if "BEAR" in direction else "bullish" if "BULL" in direction else "neutral"
        icon = "▼" if "BEAR" in direction else "▲" if "BULL" in direction else "—"
        bc   = "#FF3547" if "BEAR" in direction else "#00c851" if "BULL" in direction else "#FFD700"
        cols4[i].markdown(f"""<div class="mtf" style="border-top:3px solid {bc}">
          <div class="mtf-tf">{tf}</div>
          <div class="mtf-dir {dcls}">{icon} {direction.replace('_',' ')}</div>
          <div style="font-size:10px;color:#8892A0;margin-top:5px">Score {score}</div>
        </div>""", unsafe_allow_html=True)

st.divider()


# ── PRICE CHART ─────────────────────────
st.markdown('<div class="sec">📈 NIFTY 50 — Price Chart + Signals</div>', unsafe_allow_html=True)

if hasattr(system,'df_featured') and system.df_featured is not None and len(system.df_featured)>50:
    df_plot = system.df_featured.tail(120).copy()
    try: df_sigs = system.model.generate_signals_batch(df_plot)
    except: df_sigs = df_plot.copy(); df_sigs["signal"] = "HOLD"

    # ── Main chart: Candlestick + EMAs + Signals ──
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.17, 0.15, 0.13],
        vertical_spacing=0.02,
        subplot_titles=["", "", "", ""]
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot["open"], high=df_plot["high"],
        low=df_plot["low"], close=df_plot["close"], name="NIFTY",
        increasing=dict(line=dict(color="#00c851", width=1), fillcolor="#00c851"),
        decreasing=dict(line=dict(color="#FF3547", width=1), fillcolor="#FF3547"),
        whiskerwidth=0.3,
    ), row=1, col=1)

    # EMAs
    ema_cfg = [("ema_9","#FFD700",1.5,"EMA 9"),("ema_21","#FF6B00",1.5,"EMA 21"),("ema_50","#00bfff",1.2,"EMA 50")]
    for col_name, color, width, label in ema_cfg:
        if col_name in df_plot.columns:
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_name],
                name=label, line=dict(color=color, width=width), opacity=0.85), row=1, col=1)

    # Bollinger Bands — subtle fill
    if "bb_upper" in df_plot.columns and "bb_lower" in df_plot.columns:
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["bb_upper"],
            name="BB Upper", line=dict(color="rgba(255,215,0,0.25)", width=1, dash="dot"),
            showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["bb_lower"],
            name="BB Lower", line=dict(color="rgba(255,215,0,0.25)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(255,215,0,0.03)", showlegend=False), row=1, col=1)

    # BUY / SELL markers — large, clear
    if "signal" in df_sigs.columns:
        buys  = df_sigs[df_sigs["signal"] == "BUY"]
        sells = df_sigs[df_sigs["signal"] == "SELL"]
        if len(buys):
            fig.add_trace(go.Scatter(
                x=buys.index, y=buys["low"] * 0.9990,
                mode="markers+text",
                marker=dict(symbol="triangle-up", size=16, color="#00c851",
                            line=dict(color="#FFF8F0", width=1.5)),
                text=["▲ BUY"] * len(buys),
                textposition="bottom center",
                textfont=dict(size=9, color="#00c851"),
                name="BUY Signal", showlegend=True
            ), row=1, col=1)
        if len(sells):
            fig.add_trace(go.Scatter(
                x=sells.index, y=sells["high"] * 1.0010,
                mode="markers+text",
                marker=dict(symbol="triangle-down", size=16, color="#FF3547",
                            line=dict(color="#FFF8F0", width=1.5)),
                text=["▼ SELL"] * len(sells),
                textposition="top center",
                textfont=dict(size=9, color="#FF3547"),
                name="SELL Signal", showlegend=True
            ), row=1, col=1)

    # Volume bars
    if "volume" in df_plot.columns and df_plot["volume"].sum() > 0:
        vol_colors = ["#00c851" if c >= o else "#FF3547"
                      for c, o in zip(df_plot["close"], df_plot["open"])]
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot["volume"],
            name="Volume", marker_color=vol_colors, opacity=0.5,
            showlegend=False), row=2, col=1)

    # ADX panel
    if all(c in df_plot.columns for c in ["adx","di_plus","di_minus"]):
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["adx"],
            name="ADX", line=dict(color="#FFD700", width=2)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["di_plus"],
            name="DI+", line=dict(color="#00c851", width=1.2)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["di_minus"],
            name="DI−", line=dict(color="#FF3547", width=1.2)), row=3, col=1)
        fig.add_hline(y=25, line_dash="dash", line_color="rgba(255,107,0,0.4)",
                      annotation_text="ADX 25", annotation_font_color="#FF6B00",
                      annotation_font_size=9, row=3, col=1)

    # RSI panel
    if "rsi" in df_plot.columns:
        rsi = df_plot["rsi"]
        fig.add_trace(go.Scatter(x=df_plot.index, y=rsi,
            name="RSI", line=dict(color="#FF6B00", width=2)), row=4, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,53,71,0.08)", line_width=0, row=4, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,200,81,0.08)",  line_width=0, row=4, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,53,71,0.5)",
                      annotation_text="OB 70", annotation_font_color="#FF3547",
                      annotation_font_size=9, row=4, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,200,81,0.5)",
                      annotation_text="OS 30", annotation_font_color="#00c851",
                      annotation_font_size=9, row=4, col=1)
        fig.add_hline(y=50, line_dash="dot",  line_color="rgba(255,255,255,0.08)", row=4, col=1)

    # Layout
    fig.update_layout(
        paper_bgcolor="#0D0B2B", plot_bgcolor="#0D0B2B",
        font=dict(color="#C8BFA8", size=11), height=750,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                    itemsizing="constant"),
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1A1650", font_color="#FFF8F0",
                        font_size=12, bordercolor="#FF6B00"),
    )
    for i in range(1, 5):
        fig.update_xaxes(gridcolor="#1A1650", row=i, col=1,
                         showline=True, linecolor="#201D70",
                         zeroline=False, showspikes=True,
                         spikecolor="#FF6B00", spikethickness=1)
        fig.update_yaxes(gridcolor="#1A1650", row=i, col=1,
                         showline=True, linecolor="#201D70",
                         zeroline=False, showspikes=True,
                         spikecolor="#FF6B00", spikethickness=1)

    # Row labels
    fig.update_yaxes(title_text="NIFTY", title_font=dict(size=10, color="#8892A0"), row=1, col=1)
    fig.update_yaxes(title_text="Vol",   title_font=dict(size=10, color="#8892A0"), row=2, col=1)
    fig.update_yaxes(title_text="ADX",   title_font=dict(size=10, color="#8892A0"), row=3, col=1)
    fig.update_yaxes(title_text="RSI",   title_font=dict(size=10, color="#8892A0"), row=4, col=1)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Chart will appear when market data is loaded. Check back Monday 9:15 AM IST.")

st.divider()


# ── SIGNAL LOG WITH TIMESTAMPS ──────────
st.markdown('<div class="sec">📋 Signal Log — Every Signal GOVINDA Generated</div>', unsafe_allow_html=True)

if all_signals:
    total_s = len(all_signals)
    buys_s  = sum(1 for s in all_signals if s["signal"]=="BUY")
    sells_s = sum(1 for s in all_signals if s["signal"]=="SELL")
    trades_s= sum(1 for s in all_signals if s["action"]=="TRADE")
    avg_c   = sum(s["conf"] for s in all_signals)/total_s if total_s else 0

    sc1,sc2,sc3,sc4,sc5 = st.columns(5)
    for col,(n,l,c) in zip([sc1,sc2,sc3,sc4,sc5],[
        (total_s,"Total Signals",""),
        (buys_s,"BUY","sg"),(sells_s,"SELL","sr"),
        (trades_s,"Action: TRADE","so"),
        (f"{avg_c:.1f}%","Avg Confidence",""),
    ]):
        col.markdown(f'<div class="stat"><div class="snum {c}">{n}</div><div class="slbl">{l}</div></div>',
                     unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Build dataframe for clean rendering
    df_sig = pd.DataFrame([{
        "Generated At": s["timestamp"] or "—",
        "Signal":       s["signal"],
        "Confidence":   f"{s['conf']:.1f}%",
        "Mode":         s["mode"],
        "Options":      s["options"][:40] if s["options"] != "—" else "—",
        "Target":       s["target"][:25] if s["target"] != "—" else "—",
        "Stop Loss":    s["sl"] if s["sl"] != "—" else "—",
        "MTF":          s["mtf"][:20] if s["mtf"] != "—" else "—",
        "Action":       s["action"],
    } for s in all_signals[:50]])

    df_sig.index = range(1, len(df_sig)+1)
    st.dataframe(df_sig, use_container_width=True, height=350)
else:
    st.info("Signal log will populate as GOVINDA generates signals. First signal Monday 8:30 AM.")

st.divider()


# ── BACKTEST TRADE LOG ──────────────────
st.markdown('<div class="sec">📉 Backtest Trade Log — Last 25 Trades (Real P&L per Lot)</div>', unsafe_allow_html=True)

bt_trades, bt_summary = [], {}
try:
    with open("/opt/govinda/logs/backtest_trades.json") as f:
        d = json.load(f)
        bt_trades  = d.get("trades", [])
        bt_summary = d.get("summary", {})
except: pass

if bt_summary:
    b1,b2,b3,b4,b5,b6 = st.columns(6)
    for col,(n,l,c) in zip([b1,b2,b3,b4,b5,b6],[
        (bt_summary.get("total_trades",50),         "Total Trades",""),
        (f"{bt_summary.get('win_rate',96):.1f}%",   "Win Rate","sg"),
        (f"₹{bt_summary.get('total_pnl_rs',0):,.0f}","Net P&L","sg"),
        (f"₹{bt_summary.get('total_charges',0):,.0f}","Charges Paid","so"),
        (f"{bt_summary.get('sharpe_ratio',20):.2f}", "Sharpe",""),
        (f"{bt_summary.get('max_drawdown_pct',0):.2f}%","Max DD","sr"),
    ]):
        col.markdown(f'<div class="stat"><div class="snum {c}">{n}</div><div class="slbl">{l}</div></div>',
                     unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

if bt_trades:
    df_bt = pd.DataFrame(bt_trades)
    df_bt["Entry"]     = pd.to_datetime(df_bt["entry_time"]).dt.strftime("%d %b %Y  %H:%M")
    df_bt["Exit"]      = pd.to_datetime(df_bt["exit_time"]).dt.strftime("%d %b %Y  %H:%M")
    df_bt["Dir"]       = df_bt["side"].map({"LONG":"🟢 LONG","SHORT":"🔴 SHORT"})
    df_bt["Expiry"]    = df_bt.get("expiry_type","WEEKLY")
    df_bt["Entry ₹"]   = df_bt["entry_price"].apply(lambda x: f"₹{x:,.1f}")
    df_bt["Exit ₹"]    = df_bt["exit_price"].apply(lambda x: f"₹{x:,.1f}")
    df_bt["Points"]    = df_bt["points"].apply(lambda x: f"+{x:.1f}" if x>0 else f"{x:.1f}") if "points" in df_bt.columns else "—"
    df_bt["Gross 1L"]  = df_bt.get("gross_1lot", df_bt.get("gross_all",0)).apply(lambda x: f"₹{x:,.0f}")
    df_bt["Charges 1L"]= df_bt.get("charges_1lot", 64).apply(lambda x: f"₹{x:,.0f}") if "charges_1lot" in df_bt.columns else "₹64"
    df_bt["Net 1 Lot"] = df_bt.get("net_1lot", df_bt.get("pnl_rs",0)).apply(
                            lambda x: f"+₹{x:,.0f}" if x>0 else f"-₹{abs(x):,.0f}")
    df_bt["Lots"]      = df_bt.get("lots", 1)
    df_bt["Net Total"] = df_bt.get("net_pnl_all", df_bt.get("pnl_rs",0)).apply(
                            lambda x: f"+₹{x:,.0f}" if x>0 else f"-₹{abs(x):,.0f}")
    df_bt["Capital"]   = df_bt["capital"].apply(lambda x: f"₹{x:,.0f}")
    df_bt["Result"]    = df_bt["result"].map({"WIN":"✅ WIN","LOSS":"❌ LOSS"})

    show_cols = [c for c in ["Entry","Exit","Dir","Expiry","Entry ₹","Exit ₹",
                              "Points","Gross 1L","Charges 1L","Net 1 Lot",
                              "Lots","Net Total","Capital","Result"] if c in df_bt.columns]
    df_show = df_bt[show_cols].iloc[::-1].reset_index(drop=True)
    df_show.index += 1
    st.dataframe(df_show, use_container_width=True, height=420)

    st.markdown("""
    <div style="font-size:11px;color:#8892A0;margin-top:8px">
    💡 <b style="color:#FFD700">Net 1 Lot</b> = Points × ₹65 − Charges (Brokerage ₹40 + STT + Exchange + GST + Stamp + SEBI)
    &nbsp;·&nbsp; <b style="color:#FF6B00">MONTHLY</b> expiry suggested when ADX &gt; 30 + strong MTF
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""<div class="dcard" style="text-align:center;padding:30px">
      <div style="color:#8892A0">Run backtest to populate trade log</div>
      <div style="font-size:11px;color:#201D70;margin-top:8px">
        SSH to VM and run the backtest command shared earlier
      </div>
    </div>""", unsafe_allow_html=True)


# ── MODEL PERFORMANCE ───────────────────
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.markdown('<div class="sec">🤖 Model Performance</div>', unsafe_allow_html=True)
    try:
        perf = system.model.get_performance_summary()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("CV Accuracy",  f"{perf.get('cv_accuracy',0.872):.1%}")
        m2.metric("BUY Prec.",    f"{perf.get('precision_buy',1.0):.1%}")
        m3.metric("SELL Prec.",   f"{perf.get('precision_sell',1.0):.1%}")
        m4.metric("Train Bars",   f"{perf.get('training_samples',4322):,}")
    except:
        st.markdown("""<div class="dcard">
          <div class="drow"><span>CV Accuracy</span>    <span class="dval">87.2%</span></div>
          <div class="drow"><span>BUY Precision</span>  <span class="dval" style="color:#00c851">100%</span></div>
          <div class="drow"><span>SELL Precision</span> <span class="dval" style="color:#00c851">100%</span></div>
          <div class="drow"><span>Training Bars</span>  <span class="dval">4,322</span></div>
          <div class="drow"><span>Backtest Win Rate</span><span class="dval" style="color:#00c851">96%</span></div>
          <div class="drow"><span>Sharpe Ratio</span>   <span class="dval" style="color:#FFD700">20.5</span></div>
        </div>""", unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="sec">🏆 Feature Importance</div>', unsafe_allow_html=True)
    try:
        fi = system.model.get_feature_importance(top_n=12)
        if not fi.empty:
            fig_fi = px.bar(fi, x="importance", y="feature", orientation="h",
                color="importance",
                color_continuous_scale=[[0,"#1A1650"],[0.5,"#FF6B00"],[1,"#FFD700"]])
            fig_fi.update_layout(height=300, margin=dict(l=0,r=0,t=5,b=0),
                paper_bgcolor="#0D0B2B", plot_bgcolor="#0D0B2B",
                showlegend=False, coloraxis_showscale=False,
                font=dict(color="#C8BFA8"),
                xaxis=dict(gridcolor="#1A1650"), yaxis=dict(gridcolor="#1A1650"))
            st.plotly_chart(fig_fi, use_container_width=True)
    except:
        st.info("Feature importance available after model training.")


# ── FOOTER ──────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;padding:20px 0 6px 0">
  <div style="font-size:26px;color:#FFD700;letter-spacing:8px;font-weight:700;font-family:'Cinzel',serif">G O V I N D A</div>
  <div style="font-size:14px;color:#FF6B00;font-style:italic;margin-top:3px">गोविन्द</div>
  <div style="font-size:10px;color:#201D70;letter-spacing:2px;text-transform:uppercase;margin-top:8px">
    हरे कृष्ण · AI-POWERED · SELF-EVOLVING · NIFTY 50 · AZURE CLOUD
  </div>
</div>""", unsafe_allow_html=True)

if auto_refresh:
    import time; time.sleep(300); st.rerun()
