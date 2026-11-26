#!/usr/bin/env bash
# Summarise logs/activity.log with grep/awk: counts per level and per module.
# Usage: log_summary.sh [path-to-log]
LOG="${1:-$(dirname "$0")/../logs/activity.log}"

if [[ ! -s "$LOG" ]]; then
    echo "No log entries found at $LOG" >&2
    exit 2
fi

echo "total_entries=$(wc -l < "$LOG" | tr -d ' ')"
for lvl in INFO WARNING ERROR; do
    echo "level_${lvl}=$(grep -c "| ${lvl} |" "$LOG")"
done
awk -F' \\| ' '{ gsub("osim\\.","",$3); c[$3]++ } END { for (m in c) print "module_" m "=" c[m] }' "$LOG" | sort
echo "first_entry=$(head -1 "$LOG" | cut -d'|' -f1 | xargs)"
echo "last_entry=$(tail -1 "$LOG" | cut -d'|' -f1 | xargs)"
