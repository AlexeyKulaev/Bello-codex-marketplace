#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=".codex/bello-run"
PID_FILE="$RUN_DIR/pid"

echo "--- bello process status ---"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "status=running"
  echo "pid=$(cat "$PID_FILE")"
else
  echo "status=exited_or_missing"
fi

echo
echo "--- launch command ---"
cat "$RUN_DIR/command.txt" 2>/dev/null || true

echo
echo "--- launch parameters ---"
cat "$RUN_DIR/launch.json" 2>/dev/null || true

echo
echo "--- context ---"
cat "$RUN_DIR/context.txt" 2>/dev/null || true

echo
echo "--- bello stdout tail ---"
tail -n 100 "$RUN_DIR/bello.log" 2>/dev/null || true

echo
echo "--- bello stderr tail ---"
tail -n 60 "$RUN_DIR/bello.err.log" 2>/dev/null || true

echo
echo "--- supervisor config ---"
cat .supervisor/config.json 2>/dev/null || true

echo
echo "--- supervisor progress ---"
cat .supervisor/PROGRESS.md 2>/dev/null || true

echo
echo "--- supervisor decisions ---"
cat .supervisor/DECISIONS.md 2>/dev/null || true

echo
echo "--- last action, if available ---"
cat .supervisor/LAST_ACTION.md 2>/dev/null || true

echo
echo "--- handoff ---"
cat .supervisor/HANDOFF.md 2>/dev/null || true

echo
echo "--- health, if available ---"
cat .supervisor/HEALTH.json 2>/dev/null || true

echo
echo "--- recent events ---"
tail -n 80 .supervisor/events.jsonl 2>/dev/null || true

echo
echo "--- recent runtime log ---"
tail -n 80 .supervisor/log.jsonl 2>/dev/null || true

echo
echo "--- recent supervisor wakes ---"
tail -n 40 .supervisor/supervisor_wakes.jsonl 2>/dev/null || true

echo
echo "--- final report, if already present ---"
cat .supervisor/FINAL_REPORT.md 2>/dev/null || true

echo
echo "--- git status ---"
git status --short 2>/dev/null || true

echo
echo "--- diff stat ---"
git diff --stat 2>/dev/null || true
