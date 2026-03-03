"""
GOVINDA Holiday Checker Module
Verifies NSE/BSE trading holidays from official circular,
finds next trading day, corrects expiry dates automatically,
and determines if the system should run today.

Source: NSE Official Circular CMTR71775 (2026 Holiday Calendar)
        Verified: Feb 28, 2026
"""

from datetime import date, timedelta
from typing import Optional

# ── Official NSE/BSE Trading Holidays 2026 ────────────────────────────────────
# Source: NSE official circular CMTR71775
# Only WEEKDAY holidays listed (weekend holidays have no market impact)
# Maha Shivaratri (Feb 15 Sun), Id-ul-Fitr (Mar 21 Sat),
# Independence Day (Aug 15 Sat), Diwali Laxmi Pujan (Nov 8 Sun) → all weekends
# NOTE: Mar 2 (Holika Dahan) is NOT an official NSE holiday per NSE circular.

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26):  "Republic Day",
    date(2026, 3, 3):   "Holi",                              # Tue
    date(2026, 3, 26):  "Shri Ram Navami",                   # Thu
    date(2026, 3, 31):  "Shri Mahavir Jayanti",              # Tue
    date(2026, 4, 3):   "Good Friday",                       # Fri
    date(2026, 4, 14):  "Dr. Baba Saheb Ambedkar Jayanti",   # Tue
    date(2026, 5, 1):   "Maharashtra Day",                   # Fri
    date(2026, 5, 28):  "Bakri Eid",                         # Thu
    date(2026, 6, 26):  "Muharram",                          # Fri
    date(2026, 9, 14):  "Ganesh Chaturthi",                  # Mon
    date(2026, 10, 2):  "Mahatma Gandhi Jayanti",            # Fri
    date(2026, 10, 20): "Dussehra",                          # Tue
    date(2026, 11, 10): "Diwali Balipratipada",              # Tue
    date(2026, 11, 24): "Guru Nanak Jayanti",                # Tue
    date(2026, 12, 25): "Christmas",                         # Fri
}

# NIFTY Weekly Expiry = Tuesday (weekday index 1)
NIFTY_EXPIRY_WEEKDAY = 1


def is_trading_day(d: date) -> bool:
    """True if NSE is open on the given date."""
    if d.weekday() >= 5:
        return False
    return d not in NSE_HOLIDAYS_2026


def should_system_run(today: Optional[date] = None) -> dict:
    """
    Core gate-check: Should GOVINDA run analysis today?
    Returns decision + reason.
    """
    d = today or date.today()
    day_name = d.strftime("%A")

    if d.weekday() == 5:  # Saturday
        next_td = next_trading_day(d)
        return {
            "should_run": False,
            "mode": "OFFLINE",
            "reason": f"Saturday — market closed. Next trading day: {next_td.strftime('%a %b %d')}",
            "next_trading_day": next_td,
        }
    if d.weekday() == 6:  # Sunday
        next_td = next_trading_day(d)
        return {
            "should_run": False,
            "mode": "OFFLINE",
            "reason": f"Sunday — market closed. Next trading day: {next_td.strftime('%a %b %d')}",
            "next_trading_day": next_td,
        }
    if d in NSE_HOLIDAYS_2026:
        next_td = next_trading_day(d)
        return {
            "should_run": False,
            "mode": "OFFLINE",
            "reason": f"NSE Holiday: {NSE_HOLIDAYS_2026[d]}. Next trading day: {next_td.strftime('%a %b %d')}",
            "next_trading_day": next_td,
        }

    # It's a trading day — but what mode?
    expiry = get_next_expiry(d)
    days_to_expiry = (expiry - d).days

    if days_to_expiry == 0:
        mode = "EXPIRY_DAY"
        note = "⚠️  EXPIRY DAY — use 0DTE rules, no overnight positions"
    elif days_to_expiry == 1:
        mode = "PRE_EXPIRY"
        note = "⚠️  Day before expiry — theta decay accelerating, size down"
    else:
        mode = "NORMAL"
        note = f"{days_to_expiry} days to expiry ({expiry.strftime('%a %b %d')})"

    return {
        "should_run": True,
        "mode": mode,
        "reason": f"Regular trading day ({day_name}). {note}",
        "next_trading_day": d,
        "expiry_date": expiry,
        "days_to_expiry": days_to_expiry,
    }


def next_trading_day(from_date: Optional[date] = None) -> date:
    """Returns the next trading day AFTER the given date."""
    d = (from_date or date.today()) + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def get_next_expiry(from_date: Optional[date] = None) -> date:
    """
    Returns the next NIFTY weekly expiry (Tuesday).
    If Tuesday is a holiday → shifts to PREVIOUS trading day (NSE rule).
    If the shifted expiry has already passed → jump to following week.
    """
    d = from_date or date.today()
    days_ahead = NIFTY_EXPIRY_WEEKDAY - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    expiry = d + timedelta(days=days_ahead)

    # Shift backwards if holiday
    while not is_trading_day(expiry):
        expiry -= timedelta(days=1)

    # If shifted expiry is today or past → go to next week
    if expiry <= d:
        expiry = d + timedelta(days=days_ahead + 7)
        while not is_trading_day(expiry):
            expiry -= timedelta(days=1)

    return expiry


def week_holiday_scan(ref_date: date) -> list:
    """Returns list of holidays in the same calendar week as ref_date."""
    week_mon = ref_date - timedelta(days=ref_date.weekday())
    holidays = []
    for i in range(7):
        day = week_mon + timedelta(days=i)
        is_weekend = day.weekday() >= 5
        if day in NSE_HOLIDAYS_2026:
            holidays.append({
                "date": day,
                "name": NSE_HOLIDAYS_2026[day],
                "day": day.strftime("%A"),
                "is_weekday_closure": not is_weekend,
            })
    return holidays


def trade_calendar_summary(signal_date: Optional[date] = None) -> dict:
    """Full calendar summary for trade planning."""
    today = signal_date or date.today()
    run_check = should_system_run(today)
    entry = run_check.get("next_trading_day", next_trading_day(today))
    expiry = get_next_expiry(entry)
    days_to_expiry = (expiry - entry).days

    natural_expiry_days = NIFTY_EXPIRY_WEEKDAY - entry.weekday()
    if natural_expiry_days <= 0:
        natural_expiry_days += 7
    natural_expiry = entry + timedelta(days=natural_expiry_days)
    expiry_shifted = (natural_expiry != expiry)

    return {
        "signal_date": today.strftime("%a %b %d %Y"),
        "system_should_run": run_check["should_run"],
        "system_mode": run_check["mode"],
        "run_reason": run_check["reason"],
        "entry_day": entry.strftime("%a %b %d %Y"),
        "expiry_date": expiry.strftime("%a %b %d %Y"),
        "natural_expiry": natural_expiry.strftime("%a %b %d %Y"),
        "expiry_shifted": expiry_shifted,
        "days_to_expiry": days_to_expiry,
        "is_0dte": days_to_expiry == 0,
        "week_holidays": week_holiday_scan(entry),
    }


# ── Self-test for all scenarios ───────────────────────────────────────────────
if __name__ == "__main__":
    test_dates = [
        (date(2026, 2, 28), "Saturday — today"),
        (date(2026, 3, 2),  "Monday — Holika Dahan (NOT official holiday)"),
        (date(2026, 3, 3),  "Tuesday — Holi (official holiday)"),
        (date(2026, 3, 4),  "Wednesday — first open day of week"),
        (date(2026, 3, 9),  "Monday — day before expiry"),
        (date(2026, 3, 10), "Tuesday — expiry day"),
        (date(2026, 3, 25), "Wednesday — day before Ram Navami"),
        (date(2026, 3, 26), "Thursday — Ram Navami (holiday)"),
        (date(2026, 3, 30), "Monday — before Mahavir Jayanti expiry week"),
    ]

    print("=" * 65)
    print("GOVINDA HOLIDAY CHECKER — FULL SCENARIO TEST")
    print("Source: NSE Official Circular CMTR71775")
    print("=" * 65)

    for d, label in test_dates:
        r = should_system_run(d)
        exp = get_next_expiry(d)
        status = "🟢 RUN" if r["should_run"] else "🔴 SKIP"
        print(f"\n{d} | {label}")
        print(f"  {status} [{r['mode']:12s}] {r['reason']}")
        print(f"  Next expiry: {exp.strftime('%a %b %d')} ({(exp-d).days}d away)")
