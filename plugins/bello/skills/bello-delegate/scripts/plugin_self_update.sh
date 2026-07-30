#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE_NAME="${BELLO_CODEX_MARKETPLACE_NAME:-bello-marketplace}"
PLUGIN_NAME="${BELLO_CODEX_PLUGIN_NAME:-bello}"
PLUGIN_SELECTOR="${BELLO_CODEX_PLUGIN_SELECTOR:-${PLUGIN_NAME}@${MARKETPLACE_NAME}}"
BRANCH="${BELLO_CODEX_MARKETPLACE_BRANCH:-main}"
DEFAULT_REPO_URL="https://github.com/AlexeyKulaev/Bello-codex-marketplace.git"
RUN_DIR="${BELLO_CODEX_RUN_DIR:-.codex/bello-run}"
LOG_FILE="$RUN_DIR/plugin-self-update.log"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
usage: plugin_self_update.sh [--check-only]

Checks whether the configured Bello Codex marketplace snapshot is behind
the latest commit on refs/heads/main. If an update is available, refreshes the
marketplace snapshot, removes the installed plugin, and installs it again.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unsupported argument: $1"
      usage
      exit 2
      ;;
  esac
done

mkdir -p "$RUN_DIR"
: > "$LOG_FILE"

log() {
  printf '%s\n' "$*" | tee -a "$LOG_FILE"
}

run_logged() {
  "$@" 2>&1 | tee -a "$LOG_FILE"
  return "${PIPESTATUS[0]}"
}

run_logged_retry() {
  local attempts="$1"
  shift
  local attempt=1
  local rc=0

  while [[ "$attempt" -le "$attempts" ]]; do
    log "attempt=$attempt/$attempts command=$*"
    if run_logged "$@"; then
      return 0
    fi
    rc=$?
    if [[ "$attempt" -lt "$attempts" ]]; then
      sleep "$attempt"
    fi
    attempt=$((attempt + 1))
  done

  return "$rc"
}

fail_check() {
  log "status=check_failed"
  log "reason=$1"
  exit "${2:-30}"
}

recovery_hint() {
  log "recovery=manual"
  log "run: codex plugin marketplace upgrade $MARKETPLACE_NAME"
  log "run: codex plugin add $PLUGIN_SELECTOR"
  log "if Codex reports the plugin is already installed but stale, run:"
  log "run: codex plugin remove $PLUGIN_SELECTOR"
  log "run: codex plugin add $PLUGIN_SELECTOR"
}

normalize_git_url() {
  local source="$1"

  case "$source" in
    "" )
      printf '%s\n' "$DEFAULT_REPO_URL"
      ;;
    http://*|https://*|ssh://*|git@*|/*|./*|../* )
      printf '%s\n' "$source"
      ;;
    */* )
      printf 'https://github.com/%s.git\n' "${source%.git}"
      ;;
    * )
      printf '%s\n' "$source"
      ;;
  esac
}

read_marketplace_info() {
  local marketplace_json

  if ! marketplace_json="$(codex plugin marketplace list --json 2>>"$LOG_FILE")"; then
    return 1
  fi

  printf '%s' "$marketplace_json" | python3 -c '
import json
import sys

name = sys.argv[1]
data = json.load(sys.stdin)

for item in data.get("marketplaces", []):
    if item.get("name") != name:
        continue

    source = item.get("marketplaceSource") or {}
    print(item.get("root") or "")
    print(source.get("sourceType") or "")
    print(source.get("source") or "")
    sys.exit(0)

sys.exit(1)
' "$MARKETPLACE_NAME"
}

log "--- bello codex plugin self-update ---"
log "marketplace=$MARKETPLACE_NAME"
log "plugin=$PLUGIN_SELECTOR"
log "branch=$BRANCH"

if [[ "${BELLO_CODEX_PLUGIN_SELF_UPDATE:-1}" == "0" ]]; then
  log "status=disabled"
  exit 0
fi

MARKETPLACE_ROOT="${BELLO_CODEX_MARKETPLACE_ROOT:-}"
SOURCE_TYPE="${BELLO_CODEX_MARKETPLACE_SOURCE_TYPE:-}"
SOURCE_URL="${BELLO_CODEX_MARKETPLACE_REPO:-}"

if [[ -z "$MARKETPLACE_ROOT" ]]; then
  if ! INFO="$(read_marketplace_info 2>>"$LOG_FILE")"; then
    fail_check "marketplace_not_configured_or_unreadable" 31
  fi

  MARKETPLACE_ROOT="$(printf '%s\n' "$INFO" | sed -n '1p')"
  SOURCE_TYPE="$(printf '%s\n' "$INFO" | sed -n '2p')"
  SOURCE_URL="$(printf '%s\n' "$INFO" | sed -n '3p')"
fi

if [[ -z "$MARKETPLACE_ROOT" ]]; then
  fail_check "marketplace_root_missing" 32
fi

if [[ -n "$SOURCE_TYPE" && "$SOURCE_TYPE" != "git" ]]; then
  log "status=skipped"
  log "reason=non_git_marketplace"
  log "marketplace_root=$MARKETPLACE_ROOT"
  exit 0
fi

if ! CURRENT_HASH="$(git -C "$MARKETPLACE_ROOT" rev-parse HEAD 2>>"$LOG_FILE")"; then
  fail_check "current_commit_unreadable" 33
fi

SOURCE_URL="$(normalize_git_url "$SOURCE_URL")"
REMOTE_REF="refs/heads/$BRANCH"

if ! REMOTE_LINE="$(
  GIT_TERMINAL_PROMPT=0 \
  GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=15}" \
  git -C "$MARKETPLACE_ROOT" \
    -c http.lowSpeedLimit=1 \
    -c http.lowSpeedTime=15 \
    ls-remote "$SOURCE_URL" "$REMOTE_REF" 2>>"$LOG_FILE"
)"; then
  log "status=skipped"
  log "reason=remote_commit_unreadable"
  log "note=git remote is unreachable; continuing without plugin update"
  exit 0
fi

REMOTE_HASH="$(printf '%s\n' "$REMOTE_LINE" | awk 'NR == 1 {print $1}')"

if [[ -z "$REMOTE_HASH" ]]; then
  fail_check "remote_ref_missing:${REMOTE_REF}" 35
fi

log "marketplace_root=$MARKETPLACE_ROOT"
log "source_url=$SOURCE_URL"
log "current_commit=$CURRENT_HASH"
log "remote_commit=$REMOTE_HASH"

if [[ "$CURRENT_HASH" == "$REMOTE_HASH" ]]; then
  log "status=current"
  exit 0
fi

log "status=update_available"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  log "check_only=true"
  exit 0
fi

log "--- refreshing marketplace snapshot ---"
if ! run_logged_retry 2 codex plugin marketplace upgrade "$MARKETPLACE_NAME"; then
  fail_check "marketplace_upgrade_failed" 40
fi

PLUGIN_ROOT="$MARKETPLACE_ROOT/plugins/$PLUGIN_NAME"
PLUGIN_MANIFEST="$PLUGIN_ROOT/.codex-plugin/plugin.json"

if [[ ! -f "$PLUGIN_MANIFEST" ]]; then
  fail_check "plugin_manifest_missing_after_marketplace_upgrade:$PLUGIN_MANIFEST" 43
fi

if ! python3 -m json.tool "$PLUGIN_MANIFEST" >/dev/null 2>>"$LOG_FILE"; then
  fail_check "plugin_manifest_invalid_after_marketplace_upgrade:$PLUGIN_MANIFEST" 44
fi

log "--- removing installed plugin ---"
if ! run_logged_retry 2 codex plugin remove "$PLUGIN_SELECTOR"; then
  fail_check "plugin_remove_failed" 41
fi

log "--- installing plugin ---"
if ! run_logged_retry 3 codex plugin add "$PLUGIN_SELECTOR"; then
  recovery_hint
  fail_check "plugin_add_failed" 42
fi

log "status=updated"
log "restart_required=true"
log "note=start a new Codex thread or rerun the request so the updated skill bundle is loaded"
