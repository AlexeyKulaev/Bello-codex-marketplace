#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=".codex/bello-run"
mkdir -p "$RUN_DIR"

echo "--- bello finalization ---"
date "+%Y-%m-%dT%H:%M:%S%z" > "$RUN_DIR/finalized_at.txt"

echo
echo "--- launch command ---"
cat "$RUN_DIR/command.txt" 2>/dev/null || true

echo
echo "--- final report ---"
cat .supervisor/FINAL_REPORT.md 2>/dev/null || true

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
echo "--- supervisor handoff ---"
cat .supervisor/HANDOFF.md 2>/dev/null || true

echo
echo "--- recent events ---"
tail -n 120 .supervisor/events.jsonl 2>/dev/null || true

echo
echo "--- recent runtime log ---"
tail -n 120 .supervisor/log.jsonl 2>/dev/null || true

echo
echo "--- recent supervisor wakes ---"
tail -n 80 .supervisor/supervisor_wakes.jsonl 2>/dev/null || true

echo
echo "--- changed files ---"
git diff --name-only 2>/dev/null || true

echo
echo "--- diff stat ---"
git diff --stat 2>/dev/null || true

echo
echo "--- git status ---"
git status --short 2>/dev/null || true
