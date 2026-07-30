---
name: bello-delegate
description: Use the locally installed Bello binary to run a supervised coder/supervisor pair for coding tasks while Codex monitors progress and reports updates.
---

Use this skill when the user wants Bello to perform a coding task through its supervisor/coder workflow.

Core contract:

- Bello does the coding work.
- Codex observes, monitors, explains, and summarizes.
- Codex must not directly edit project code unless the user explicitly asks.
- Bello must be installed separately and available as `bello` in PATH.
- Adapter scripts must be resolved relative to this skill directory, not relative to the target project.

Path resolution rule:

* Let `SKILL_DIR` mean the installed directory that contains this `SKILL.md`.
* Do not run scripts through repo-relative paths such as `plugins/bello/skills/bello-delegate/scripts/...`.
* In normal user projects, that repo-relative path will not exist.
* Instead, run scripts by absolute path under this installed skill directory:

  * `$SKILL_DIR/scripts/plugin_self_update.sh`
  * `$SKILL_DIR/scripts/preflight_update.sh`
  * `$SKILL_DIR/scripts/start_bello.sh`
  * `$SKILL_DIR/scripts/check_bello.sh`
  * `$SKILL_DIR/scripts/finalize_bello.sh`

Plugin self-update rule:

* At the start of every skill invocation, before Bello preflight and before
  starting work, run:

  `$SKILL_DIR/scripts/plugin_self_update.sh`

* The script compares the configured `bello-marketplace` Git snapshot commit
  with the latest `refs/heads/main` commit from its Git remote.
* If an update is available, the script refreshes the marketplace, verifies the
  plugin manifest, removes the installed plugin, then reinstalls it with
  bounded retries and manual recovery commands on failure.
* If the script prints `status=current`, continue normally.
* If the script prints `status=updated`, stop this invocation after reporting
  that the plugin was updated. Tell the user to start a new Codex thread or
  rerun the request so Codex loads the updated skill bundle.
* If the command cannot reach the Git remote, treat it as a network problem:
  report that the update check was skipped and continue with the installed
  plugin.
* If Codex needs filesystem or network approval to read `~/.codex`, run
  `git ls-remote`, refresh the marketplace, remove the plugin, or install the
  plugin, request that approval and retry once.
* If marketplace refresh, plugin removal, or plugin installation fails after an
  update was detected, report the self-update failure and do not start Bello.

Release rule for plugin updates:

* Every published plugin update must bump `.codex-plugin/plugin.json` `version`.
  The commit-hash check detects that the marketplace snapshot is behind, but
  Codex caches installed plugin bundles by plugin identity and version.

Before starting Bello, read:

* `$SKILL_DIR/references/COMMAND_ORDER.md`
* `$SKILL_DIR/references/BELLO_RUNTIME.md`

Workflow:

1. Run plugin self-update.

   Run:

   `$SKILL_DIR/scripts/plugin_self_update.sh`

   If the script installs an update, stop and ask the user to rerun the request
   in a new thread. Do not start Bello from the stale skill bundle.

2. Parse the user request.

   Extract supported Bello parameters only:

   * task file, usually `TASK.md`;
   * `--coder-mod MODEL`, if provided;
   * `--super-mod MODEL`, if provided;
   * `--coder-intelligence low|medium|high|xhigh`, if provided;
   * `--super-intelligence low|medium|high|xhigh`, if provided;
   * `--fast[=true|false]`, if provided;
   * `--start-over[=true|false]`, if provided;
   * `--clean[=true|false]`, only if explicitly provided;
   * `--completion-review[=true|false]`, if provided;
   * `--adversary[=true|false]`, if provided;
   * `--adversary-runs N`, if provided;
   * repeated `--protected-path PATH`, if provided.

   Do not invent parameter values.

   `--model` is not a current Bello flag. If the user asks for it, tell them
   to use `--coder-mod MODEL --super-mod MODEL`.

   If the user provides `--coder-mod` without `--super-mod`, or `--super-mod` without `--coder-mod`, stop and ask for the missing paired parameter.

   Reject unknown Bello arguments instead of silently forwarding them.

3. Run Bello preflight and update.

   Run:

   `$SKILL_DIR/scripts/preflight_update.sh`

   If Bello is missing, tell the user how to install it and stop.

   If Bello reports that an update is available, run `bello update` through the preflight script before starting work.

   If `bello doctor` fails, stop and report the failure. Do not start Bello.

4. Start Bello in the background.

   Run:

   `$SKILL_DIR/scripts/start_bello.sh --task <task-file> [bello-options...]`

   Preserve all supported parameters from the user request.

   The command must be built in the order described in `COMMAND_ORDER.md`.

   After start, report to the user:

   * whether Bello started or failed to start;
   * task file;
   * exact parameters passed;
   * log path: `.codex/bello-run/`;
   * state path: `.supervisor/`.

5. Monitor Bello.

   While Bello is running, periodically run:

   `$SKILL_DIR/scripts/check_bello.sh`

   Use the latest checkpoint observation to report progress. Do not claim true continuous streaming.

   Primary monitoring sources:

   * `.supervisor/config.json`
   * `.supervisor/PROGRESS.md`
   * `.supervisor/DECISIONS.md`
   * `.supervisor/HANDOFF.md`
   * `.supervisor/events.jsonl`
   * `.supervisor/log.jsonl`
   * `.supervisor/supervisor_wakes.jsonl`
   * `.supervisor/FINAL_REPORT.md`, if present

   Secondary monitoring sources:

   * `.codex/bello-run/command.txt`
   * `.codex/bello-run/launch.json`
   * `.codex/bello-run/context.txt`
   * `.codex/bello-run/bello.log`
   * `.codex/bello-run/bello.err.log`
   * `git status --short`
   * `git diff --stat`

   Progress reports should include:

   * running/exited status;
   * current phase;
   * supervisor/coder decision;
   * files changed;
   * validation status;
   * blockers;
   * next expected step.

6. Detect launch failures.

   If Bello exits but `.supervisor/` was never created, treat this as a launch failure, not a normal empty run.

   Report:

   * command from `.codex/bello-run/command.txt`;
   * launch parameters from `.codex/bello-run/launch.json`;
   * stdout tail from `.codex/bello-run/bello.log`;
   * stderr tail from `.codex/bello-run/bello.err.log`;
   * whether `.supervisor/` exists.

7. Finalize after Bello exits.

   Run:

   `$SKILL_DIR/scripts/finalize_bello.sh`

   The final report must be based primarily on:

   * `.supervisor/FINAL_REPORT.md`
   * `git diff --stat`
   * `git diff --name-only`
   * `git status --short`

8. Final response.

   Summarize:

   * final outcome;
   * changed files;
   * validation;
   * risks;
   * unresolved blockers;
   * recommended next action.

Important safety notes:

* Do not use `--clean` unless the user explicitly requested it.
* Do not mutate `.supervisor/` manually.
* Do not edit project code yourself unless the user explicitly asks.
* Do not run `codex login` automatically. If auth is missing, tell the user to log in manually.
* Do not start a new Bello run if an existing valid Bello process is already running for the current workspace.
* If startup logs are empty, `.supervisor/` is missing, and the Bello PID has exited, report a launch failure instead of continuing.
