Bello is a terminal supervisor for autonomous Codex runs.

Bello lets a Codex coding agent work in a project while a separate
supervisor/controller owns approvals, steering, restarts, state, and final
completion.

Bello does not drive Codex through hooks, plugins, subagents, or
`codex exec --json`. It starts `codex app-server --listen stdio://` and
communicates with Codex through the app-server JSON-RPC protocol.

## Main Flow

From a target project, run:

```bash
bello --task TASK.md
```

If `--task` is omitted, Bello scans for markdown task files and opens a
selector when there are multiple candidates.

Preferred task names:

- `TASK.md`
- `task.md`
- `PLAN.md`
- `plan.md`
- `TODO.md`

## Runtime Roles

Bello has two Codex roles:

- Coder: a persistent Codex thread that reads the selected task, edits files,
  runs commands, and validates work.
- Supervisor: short stateless Codex turns that review approvals and runtime
  state, steer or restart the coder, and accept or return final readiness.

The Codex plugin must not act as the coder unless the user explicitly asks.

The plugin should:

- launch Bello;
- monitor Bello state;
- inspect `.supervisor/`;
- inspect `git status` and `git diff`;
- report progress to the user;
- summarize final output.

## Safety Model

Bello owns approval handling during a normal run.

It can:

- allow safe read-only inspection;
- allow ordinary workspace edits;
- deny dangerous actions such as secret access, destructive commands, broad
  permission changes, deploy/publish commands, git force operations, and
  `.supervisor` mutations;
- route gray-zone actions to supervisor review;
- fail closed for unsupported approval surfaces.

## State And Reports

Bello writes runtime state into `.supervisor/` in the target project.

Important files:

- `.supervisor/config.json`: selected task, models, Codex version, schema hash,
  threads, generation, and status.
- `.supervisor/PROGRESS.md`: durable supervisor progress notes.
- `.supervisor/DECISIONS.md`: durable supervisor decisions.
- `.supervisor/HANDOFF.md`: restart handoff context.
- `.supervisor/events.jsonl`: normalized event stream.
- `.supervisor/log.jsonl`: runtime log.
- `.supervisor/supervisor_wakes.jsonl`: supervisor wake audit stream.
- `.supervisor/FINAL_REPORT.md`: final status, changed files, validation, and
  risks.

For progress reports, prefer compact state files over raw terminal logs.
