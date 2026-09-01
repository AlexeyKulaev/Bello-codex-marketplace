# Advice output contract

Return exactly one selected setup and nothing else.

The first line contains the planning parameter:

```text
Plan: none
```

or, when a separate planning pass is selected:

```text
Plan: gpt-5.6-terra max -> PLAN.md
```

The planning line is outside `ProjectConfig` because the plan is prepared before Bello and passed with `--plan`.

Immediately after that line, emit exactly one complete JSON code block containing the selected Bello `ProjectConfig`. Include every field required by [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md): all primary and revision role profiles, explicit bounded review settings, `speed`, `cheap_runtime`, preserved project fields, and the three independent multi-agent policy objects.

Set `task` to the exact input task file as a normalized project-root-relative path with `/` separators. It must be non-empty and must not be `null`, absolute, drive-relative, UNC, contain `..`, or retain a temporary-workspace prefix.

Do not include a heading, recommendation label, rationale, task summary, evidence, assumptions, alternatives, cost, time, quality estimate, model comparison, source, citation, confidence statement, validation narration, compatibility narration, or advice wrapper. Do not add `planning`, `plan`, or `plan_path` to the config JSON. Do not emit runtime-owned state.

Validate the selected config silently against [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md) and `scripts/validate_config.py` before returning it. When commands are allowed, pass `--project-root PROJECT_ROOT --task-file TASK_FILE` so the validator checks that the JSON names the exact resolved task. If validation or a checked installed-version compatibility test fails, return only the concise blocker instead of an invalid configuration.
