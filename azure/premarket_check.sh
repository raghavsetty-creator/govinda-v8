#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# GOVINDA Pre-Market Checklist & Auto-Fix
# Run every morning at 08:30 AM IST before market opens
# Usage: bash /opt/govinda/premarket_check.sh
# ═══════════════════════════════════════════════════════════════════

LOG="/opt/govinda/logs/cron.log"
PASS=0; FAIL=0; FIXED=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

pass()  { echo -e "${GREEN}  ✅ $1${NC}"; ((PASS++)); }
fail()  { echo -e "${RED}  ❌ $1${NC}"; ((FAIL++)); }
fixed() { echo -e "${YELLOW}  🔧 FIXED — $1${NC}"; ((FIXED++)); }
info()  { echo -e "${BLUE}  ▶ $1${NC}"; }
log()   { echo "[$(date '+%Y-%m-%d %H:%M:%S IST')] $1" >> "$LOG"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     GOVINDA Pre-Market Checklist — $(date '+%d %b %Y %I:%M %p IST')     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
log "=== Pre-market check started ==="

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 1: CHECK TRADING DAY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

RESULT=$(cd /opt/govinda/app && /opt/govinda/venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv('/opt/govinda/.env')
from utils.holiday_checker import should_system_run
r = should_system_run()
print(r['mode'], '|', r['reason'])
" 2>/dev/null)

MODE=$(echo "$RESULT" | cut -d'|' -f1 | tr -d ' ')
REASON=$(echo "$RESULT" | cut -d'|' -f2 | xargs)

echo "  📅 Mode   : $MODE"
echo "  📋 Reason : $REASON"

if [ "$MODE" = "OFFLINE" ]; then
    echo -e "${YELLOW}  ⚠️  Today is a holiday/weekend — GOVINDA will run in OFFLINE mode${NC}"
    echo "  ℹ️  No trades will be executed today"
    log "OFFLINE mode: $REASON"
else
    pass "Trading day confirmed: $MODE"
    log "Trading day: $MODE — $REASON"
fi

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 2: ENGINE STATUS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

ENGINE=$(sudo systemctl is-active govinda-engine 2>/dev/null)
if [ "$ENGINE" = "active" ]; then
    UPTIME=$(sudo systemctl status govinda-engine --no-pager 2>/dev/null | grep "Active:" | awk '{print $4,$5,$6}')
    pass "Engine running — $UPTIME"
    log "Engine: active"
else
    fail "Engine not running ($ENGINE) — attempting fix..."
    sudo systemctl start govinda-engine
    sleep 5
    ENGINE2=$(sudo systemctl is-active govinda-engine 2>/dev/null)
    if [ "$ENGINE2" = "active" ]; then
        fixed "Engine started successfully"
        log "Engine: started by premarket check"
    else
        fail "Engine FAILED to start — check logs"
        log "Engine: FAILED to start"
        echo "  🔍 Last error:"
        sudo journalctl -u govinda-engine -n 5 --no-pager | tail -3
    fi
fi

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 3: DASHBOARD STATUS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

DASH=$(sudo systemctl is-active govinda-dashboard 2>/dev/null)
if [ "$DASH" = "active" ]; then
    pass "Dashboard running"
    log "Dashboard: active"
else
    fail "Dashboard not running — attempting fix..."
    fuser -k 8501/tcp 2>/dev/null
    sleep 2
    sudo systemctl start govinda-dashboard
    sleep 5
    DASH2=$(sudo systemctl is-active govinda-dashboard 2>/dev/null)
    if [ "$DASH2" = "active" ]; then
        fixed "Dashboard started successfully"
        log "Dashboard: started by premarket check"
    else
        fail "Dashboard FAILED to start"
        log "Dashboard: FAILED to start"
    fi
fi

# HTTP check
HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 2>/dev/null)
[ "$HTTP" = "200" ] && pass "Dashboard HTTP 200 OK" || fail "Dashboard HTTP: $HTTP"

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 4: API KEYS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

for key in ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY; do
    VAL=$(grep "^${key}=" /opt/govinda/.env 2>/dev/null | cut -d'=' -f2)
    if [ -n "$VAL" ]; then
        pass "$key set (${#VAL} chars)"
    else
        fail "$key MISSING — add to /opt/govinda/.env"
        log "MISSING KEY: $key"
    fi
done

# Verify keys actually work
AI_STATUS=$(cd /opt/govinda/app && /opt/govinda/venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv('/opt/govinda/.env')
from ai_brain.multi_ai import AIBrain
b = AIBrain(); s = b.get_status()
print('claude='+str(s.get('claude',False))+' gpt4='+str(s.get('gpt4',False))+' gemini='+str(s.get('gemini',False)))
" 2>/dev/null)

echo "  🤖 AI Status: $AI_STATUS"
echo "$AI_STATUS" | grep -q "claude=True"  && pass "Claude connected"  || fail "Claude NOT connected"
echo "$AI_STATUS" | grep -q "gpt4=True"    && pass "GPT-4 connected"   || fail "GPT-4 NOT connected"
echo "$AI_STATUS" | grep -q "gemini=True"  && pass "Gemini connected"  || fail "Gemini NOT connected"

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 5: DATA FETCH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

CANDLES=$(cd /opt/govinda/app && /opt/govinda/venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv('/opt/govinda/.env')
from data.fetcher import DataFetcher
f = DataFetcher(); df = f.fetch_historical(); print(len(df))
" 2>/dev/null)

HOUR=$(TZ=Asia/Kolkata date +%H)
if [ -n "$CANDLES" ] && [ "$CANDLES" -gt 0 ] 2>/dev/null; then
    pass "Data fetch working — $CANDLES candles"
    log "Data: $CANDLES candles fetched"
elif [ "$HOUR" -lt 9 ] || [ "$HOUR" -ge 16 ]; then
    echo -e "${YELLOW}  ⏳ Outside market hours — data fetch OK after 09:15 AM${NC}"
elif [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 16 ]; then
    fail "Data fetch returned 0 candles during market hours"
else
    echo -e "${YELLOW}  ⏳ Market not open yet${NC}"
    log "Data: 0 candles during market hours"
fi

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 6: DISK & MEMORY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

# Disk space
DISK=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK" -lt 80 ]; then
    pass "Disk space OK — ${DISK}% used"
else
    fail "Disk space LOW — ${DISK}% used — run: sudo apt autoremove"
fi

# Memory
MEM=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
if [ "$MEM" -lt 85 ]; then
    pass "Memory OK — ${MEM}% used"
else
    fail "Memory HIGH — ${MEM}% used"
    # Clear cache
    sudo sync && sudo echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    fixed "Memory cache cleared"
fi

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 7: LOG HEALTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

# Log size check — rotate if too large (>50MB)
LOG_SIZE=$(du -sm /opt/govinda/logs/engine.log 2>/dev/null | cut -f1)
if [ -n "$LOG_SIZE" ] && [ "$LOG_SIZE" -gt 50 ]; then
    cp /opt/govinda/logs/engine.log "/opt/govinda/logs/engine_$(date +%Y%m%d).log"
    echo "" > /opt/govinda/logs/engine.log
    fixed "Engine log rotated (was ${LOG_SIZE}MB)"
    log "Log rotated: ${LOG_SIZE}MB"
else
    pass "Log size OK — ${LOG_SIZE:-0}MB"
fi

# Logs writable
touch /opt/govinda/logs/test_write 2>/dev/null \
    && rm /opt/govinda/logs/test_write \
    && pass "Logs directory writable" \
    || fail "Logs directory NOT writable"

# ─────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}━━━ STEP 8: WATCHDOG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
# ─────────────────────────────────────────────────────────────────

[ -x "/opt/govinda/watchdog.sh" ] \
    && pass "Watchdog script ready" \
    || fail "Watchdog script missing/not executable"

crontab -l 2>/dev/null | grep -q "watchdog" \
    && pass "Watchdog cron active" \
    || fail "Watchdog cron missing"

# ─────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  PRE-MARKET SUMMARY                        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo -e "║  ${GREEN}PASS  : $PASS${NC}                                               ║"
echo -e "║  ${RED}FAIL  : $FAIL${NC}                                               ║"
echo -e "║  ${YELLOW}FIXED : $FIXED${NC}                                               ║"
echo "╠══════════════════════════════════════════════════════════════╣"

if [ $FAIL -eq 0 ]; then
    echo -e "║  ${GREEN}🚀 ALL CLEAR — GOVINDA READY FOR MARKET OPEN!${NC}             ║"
    echo "║  📊 Dashboard: http://20.235.81.186:8501                   ║"
    log "Pre-market check: ALL CLEAR — $PASS passed, $FIXED fixed"
else
    echo -e "║  ${RED}⚠️  $FAIL ISSUE(S) NEED ATTENTION BEFORE TRADING${NC}           ║"
    log "Pre-market check: $FAIL FAILURES — action required"
fi
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
