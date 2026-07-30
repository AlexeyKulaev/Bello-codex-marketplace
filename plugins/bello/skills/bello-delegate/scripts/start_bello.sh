#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=".codex/bello-run"
PROJECT_DIR="$(pwd -P)"
mkdir -p "$RUN_DIR"

TASK_FILE=""
CODER_MOD=""
SUPER_MOD=""
CODER_INTELLIGENCE=""
SUPER_INTELLIGENCE=""
FAST=""
START_OVER=""
CLEAN=""
COMPLETION_REVIEW=""
ADVERSARY=""
ADVERSARY_RUNS=""
PROTECTED_PATHS=()

take_required_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "missing value for $flag"
    exit 2
  fi
  printf '%s\n' "$value"
}

take_optional_bool() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    printf 'true\n'
    return 0
  fi
  printf '%s\n' "$value"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK_FILE="${2:?missing value for --task}"
      shift 2
      ;;
    --task=*)
      TASK_FILE="${1#*=}"
      shift
      ;;
    --model|--model=*)
      echo "unsupported argument: --model"
      echo "Current Bello uses --coder-mod MODEL --super-mod MODEL instead."
      exit 2
      ;;
    --coder-mod)
      CODER_MOD="$(take_required_value "$1" "${2:-}")"
      shift 2
      ;;
    --coder-mod=*)
      CODER_MOD="${1#*=}"
      shift
      ;;
    --super-mod)
      SUPER_MOD="$(take_required_value "$1" "${2:-}")"
      shift 2
      ;;
    --super-mod=*)
      SUPER_MOD="${1#*=}"
      shift
      ;;
    --coder-intelligence)
      CODER_INTELLIGENCE="$(take_required_value "$1" "${2:-}")"
      shift 2
      ;;
    --coder-intelligence=*)
      CODER_INTELLIGENCE="${1#*=}"
      shift
      ;;
    --super-intelligence)
      SUPER_INTELLIGENCE="$(take_required_value "$1" "${2:-}")"
      shift 2
      ;;
    --super-intelligence=*)
      SUPER_INTELLIGENCE="${1#*=}"
      shift
      ;;
    --fast)
      FAST="$(take_optional_bool "$1" "${2:-}")"
      if [[ $# -gt 1 && "$2" != --* ]]; then shift 2; else shift; fi
      ;;
    --fast=*)
      FAST="${1#*=}"
      shift
      ;;
    --start-over)
      START_OVER="$(take_optional_bool "$1" "${2:-}")"
      if [[ $# -gt 1 && "$2" != --* ]]; then shift 2; else shift; fi
      ;;
    --start-over=*)
      START_OVER="${1#*=}"
      shift
      ;;
    --clean)
      CLEAN="$(take_optional_bool "$1" "${2:-}")"
      if [[ $# -gt 1 && "$2" != --* ]]; then shift 2; else shift; fi
      ;;
    --clean=*)
      CLEAN="${1#*=}"
      shift
      ;;
    --completion-review)
      COMPLETION_REVIEW="$(take_optional_bool "$1" "${2:-}")"
      if [[ $# -gt 1 && "$2" != --* ]]; then shift 2; else shift; fi
      ;;
    --completion-review=*)
      COMPLETION_REVIEW="${1#*=}"
      shift
      ;;
    --adversary)
      ADVERSARY="$(take_optional_bool "$1" "${2:-}")"
      if [[ $# -gt 1 && "$2" != --* ]]; then shift 2; else shift; fi
      ;;
    --adversary=*)
      ADVERSARY="${1#*=}"
      shift
      ;;
    --adversary-runs)
      ADVERSARY_RUNS="$(take_required_value "$1" "${2:-}")"
      shift 2
      ;;
    --adversary-runs=*)
      ADVERSARY_RUNS="${1#*=}"
      shift
      ;;
    --protected-path)
      PROTECTED_PATHS+=("$(take_required_value "$1" "${2:-}")")
      shift 2
      ;;
    --protected-path=*)
      PROTECTED_PATHS+=("${1#*=}")
      shift
      ;;
    *)
      echo "unsupported argument: $1"
      echo "Supported: --task --coder-mod --super-mod --coder-intelligence --super-intelligence --fast --start-over --clean --completion-review --adversary --adversary-runs --protected-path"
      exit 2
      ;;
  esac
done

if [[ -z "$TASK_FILE" ]]; then
  TASK_FILE="TASK.md"
fi

if [[ ! -f "$TASK_FILE" ]]; then
  echo "task file not found: $TASK_FILE"
  exit 2
fi

if [[ -n "$CODER_MOD" && -z "$SUPER_MOD" ]]; then
  echo "--coder-mod requires --super-mod"
  exit 2
fi

if [[ -z "$CODER_MOD" && -n "$SUPER_MOD" ]]; then
  echo "--super-mod requires --coder-mod"
  exit 2
fi

is_existing_bello_run() {
  local pid="$1"

  if ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi

  local proc_cwd=""
  local proc_cmd=""

  if [[ -r "/proc/$pid/cmdline" ]]; then
    # Linux: read process info from /proc.
    proc_cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    proc_cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  else
    # macOS/BSD: no /proc; use lsof for cwd and ps for the command line.
    proc_cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
    proc_cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  fi

  [[ "$proc_cwd" == "$PROJECT_DIR" && "$proc_cmd" == *bello* ]]
}

PID_FILE="$RUN_DIR/pid"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"

  if [[ -n "$OLD_PID" ]] && is_existing_bello_run "$OLD_PID"; then
    echo "bello already running pid=$OLD_PID"
    exit 0
  fi

  echo "removing stale pid file"
  rm -f "$PID_FILE"
fi

cmd=(bello)

# Order follows COMMAND_ORDER.md / tt.md.
cmd+=(--task "$TASK_FILE")

if [[ -n "$CODER_MOD" && -n "$SUPER_MOD" ]]; then
  cmd+=(--coder-mod "$CODER_MOD")
  cmd+=(--super-mod "$SUPER_MOD")
fi

if [[ -n "$CODER_INTELLIGENCE" ]]; then
  cmd+=(--coder-intelligence "$CODER_INTELLIGENCE")
fi

if [[ -n "$SUPER_INTELLIGENCE" ]]; then
  cmd+=(--super-intelligence "$SUPER_INTELLIGENCE")
fi

if [[ -n "$FAST" ]]; then
  cmd+=(--fast "$FAST")
fi

if [[ -n "$START_OVER" ]]; then
  cmd+=(--start-over "$START_OVER")
fi

if [[ -n "$CLEAN" ]]; then
  cmd+=(--clean "$CLEAN")
fi

if [[ -n "$COMPLETION_REVIEW" ]]; then
  cmd+=(--completion-review "$COMPLETION_REVIEW")
fi

if [[ -n "$ADVERSARY" ]]; then
  cmd+=(--adversary "$ADVERSARY")
fi

if [[ -n "$ADVERSARY_RUNS" ]]; then
  cmd+=(--adversary-runs "$ADVERSARY_RUNS")
fi

# ${arr[@]+...} guard: plain "${arr[@]}" on an empty array is an unbound-variable
# error under `set -u` in bash 3.2 (default shell on macOS).
for path in ${PROTECTED_PATHS[@]+"${PROTECTED_PATHS[@]}"}; do
  cmd+=(--protected-path "$path")
done

date "+%Y-%m-%dT%H:%M:%S%z" > "$RUN_DIR/started_at.txt"
git status --short > "$RUN_DIR/status.before" 2>/dev/null || true

{
  printf 'argv:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
} > "$RUN_DIR/command.txt"

python3 - "$RUN_DIR/launch.json" \
  "$PROJECT_DIR" \
  "$TASK_FILE" \
  "$CODER_MOD" \
  "$SUPER_MOD" \
  "$CODER_INTELLIGENCE" \
  "$SUPER_INTELLIGENCE" \
  "$FAST" \
  "$START_OVER" \
  "$CLEAN" \
  "$COMPLETION_REVIEW" \
  "$ADVERSARY" \
  "$ADVERSARY_RUNS" \
  ${PROTECTED_PATHS[@]+"${PROTECTED_PATHS[@]}"} <<'PY'
import json
import sys

out = sys.argv[1]
project_dir = sys.argv[2]
task_file = sys.argv[3]
coder_mod = sys.argv[4]
super_mod = sys.argv[5]
coder_intelligence = sys.argv[6]
super_intelligence = sys.argv[7]
fast = sys.argv[8]
start_over = sys.argv[9]
clean = sys.argv[10]
completion_review = sys.argv[11]
adversary = sys.argv[12]
adversary_runs = sys.argv[13]
protected_paths = sys.argv[14:]


def optional_bool(value):
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return value

data = {
    "project_dir": project_dir,
    "task_file": task_file,
    "coder_mod": coder_mod or None,
    "super_mod": super_mod or None,
    "coder_intelligence": coder_intelligence or None,
    "super_intelligence": super_intelligence or None,
    "fast": optional_bool(fast),
    "start_over": optional_bool(start_over),
    "clean": optional_bool(clean),
    "completion_review": optional_bool(completion_review),
    "adversary": optional_bool(adversary),
    "adversary_runs": int(adversary_runs) if adversary_runs else None,
    "protected_paths": protected_paths,
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

cat > "$RUN_DIR/context.txt" <<'EOF'
Bello is the runtime executor.
Codex plugin is the observer/reporter.
Bello writes durable state into `.supervisor/`.
Codex should monitor `.supervisor/*`, git status, and git diff.
EOF

echo "--- launching bello ---"
cat "$RUN_DIR/command.txt"

# `&` alone is not enough in Codex/tool environments.
# Use nohup + setsid so the process is not tied to the launching shell/session.
# macOS has no setsid binary; plain nohup is NOT enough there because the
# process stays in the caller's process group and gets killed when the
# launching tool command finishes. Start a new session via python3 instead.
if command -v setsid >/dev/null 2>&1; then
  nohup setsid "${cmd[@]}" \
    > "$RUN_DIR/bello.log" \
    2> "$RUN_DIR/bello.err.log" \
    < /dev/null &
  PID="$!"
else
  PID="$(python3 - "$RUN_DIR/bello.log" "$RUN_DIR/bello.err.log" "${cmd[@]}" <<'PYLAUNCH'
import os
import subprocess
import sys

log_path, err_path = sys.argv[1], sys.argv[2]
cmd = sys.argv[3:]
with open(log_path, "ab") as log, open(err_path, "ab") as err, \
        open(os.devnull, "rb") as devnull:
    proc = subprocess.Popen(
        cmd, stdout=log, stderr=err, stdin=devnull, start_new_session=True
    )
print(proc.pid)
PYLAUNCH
)"
fi

echo "$PID" > "$PID_FILE"
echo "started bello pid=$PID"

echo "--- readiness check ---"

attempt=1
while [[ "$attempt" -le 30 ]]; do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "status=exited_during_startup"
    echo "--- command ---"
    cat "$RUN_DIR/command.txt" 2>/dev/null || true
    echo "--- stdout ---"
    cat "$RUN_DIR/bello.log" 2>/dev/null || true
    echo "--- stderr ---"
    cat "$RUN_DIR/bello.err.log" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 10
  fi

  if [[ -d ".supervisor" ]] || [[ -s "$RUN_DIR/bello.log" ]] || [[ -s "$RUN_DIR/bello.err.log" ]]; then
    echo "status=started_observed"
    exit 0
  fi

  sleep 1
  attempt=$((attempt + 1))
done

echo "status=running_but_no_state_observed_yet"
echo "pid=$PID"
exit 0
