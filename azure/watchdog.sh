#!/bin/bash
export TZ=Asia/Kolkata
LOG="/opt/govinda/logs/cron.log"
timestamp() { date '+%Y-%m-%d %H:%M:%S IST'; }
HOUR=$(date +%H)
if [ "$HOUR" -lt 9 ] || [ "$HOUR" -gt 15 ]; then exit 0; fi
LAST=$(stat -c %Y /opt/govinda/logs/engine.log 2>/dev/null)
NOW=$(date +%s)
DIFF=$((NOW - LAST))
if [ "$DIFF" -gt 600 ]; then
    echo "[$(timestamp)] ⚠️  Engine silent ${DIFF}s — restarting" >> "$LOG"
    sudo systemctl restart govinda-engine
fi
if ! curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "[$(timestamp)] ⚠️  Dashboard not responding — restarting" >> "$LOG"
    sudo systemctl restart govinda-dashboard
fi
