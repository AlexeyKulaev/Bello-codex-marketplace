#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=".codex/bello-run"
mkdir -p "$RUN_DIR"

echo "--- checking bello binary ---"

if ! command -v bello >/dev/null 2>&1; then
  echo "status=missing"
  echo "bello binary not found in PATH"
  echo "install: pipx install bello"
  exit 127
fi

echo "status=found"
command -v bello | tee "$RUN_DIR/bello.path.txt"

echo
echo "--- environment checks ---"
python3 --version 2>&1 | tee "$RUN_DIR/python.version.txt" || true
git --version 2>&1 | tee "$RUN_DIR/git.version.txt" || true
codex --version 2>&1 | tee "$RUN_DIR/codex.version.txt" || true

echo
echo "--- codex app-server schema check ---"
codex app-server generate-json-schema --experimental --out /tmp/bello-schema-check \
  > "$RUN_DIR/codex.schema.log" 2>&1 || true
cat "$RUN_DIR/codex.schema.log"

echo
echo "--- bello version before update ---"
bello --version | tee "$RUN_DIR/version.before.txt" || true

echo
echo "--- bello doctor before update ---"
set +e
bello doctor > "$RUN_DIR/doctor.before.txt" 2>&1
DOCTOR_EXIT=$?
set -e

cat "$RUN_DIR/doctor.before.txt"

if [[ "$DOCTOR_EXIT" -ne 0 ]]; then
  echo "bello doctor failed before update"
  echo "Not running Bello task."
  exit "$DOCTOR_EXIT"
fi

echo
echo "--- update detection ---"

UPDATE_AVAILABLE=false
if bello update --check --json > "$RUN_DIR/update.check.json" 2> "$RUN_DIR/update.check.err"; then
  cat "$RUN_DIR/update.check.json"
  UPDATE_AVAILABLE="$(python3 - "$RUN_DIR/update.check.json" <<'PY'
import json
import sys

try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("false")
else:
    print("true" if payload.get("update_available") is True else "false")
PY
)"
else
  echo "bello update --check --json failed; falling back to text detection"
  cat "$RUN_DIR/update.check.err" || true
  if grep -Eiq "update available|new version|out of date|outdated|behind" \
    "$RUN_DIR/doctor.before.txt" "$RUN_DIR/version.before.txt"; then
    UPDATE_AVAILABLE=true
  fi
fi

if [[ "$UPDATE_AVAILABLE" == "true" ]]; then

  echo "update_available=true"
  echo "--- running bello update ---"
  bello update | tee "$RUN_DIR/update.log"

  echo
  echo "--- bello version after update ---"
  bello --version | tee "$RUN_DIR/version.after.txt" || true

  echo
  echo "--- bello doctor after update ---"
  bello doctor | tee "$RUN_DIR/doctor.after.txt"
else
  echo "update_available=false"
fi
