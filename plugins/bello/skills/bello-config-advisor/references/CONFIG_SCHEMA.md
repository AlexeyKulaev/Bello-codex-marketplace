# Current Bello configuration schema

This reference targets Bello 0.5.0's user-facing `ProjectConfig`. The persistent file is `.supervisor/config.json`, but it also contains runtime state after a run starts. Never replace that file directly or feed it directly to the advisor validator; first extract the project settings with `scripts/inspect_config.py`.

The inspector deliberately preserves valid dormant values such as saved review budgets while their feature is off. Its `current_project_config` is a baseline for comparison, not necessarily valid under the advisor's stricter canonical output policy. Overlay all selected review fields and zero inactive budgets before running `validate_config.py`.

## Fully resolved shape

```json
{
  "review_limit_format": "explicit",
  "task": "TASK.md",
  "coder_mod": "gpt-5.6-luna",
  "revision_coder_enabled": false,
  "revision_coder_mod": "gpt-5.6-luna",
  "runtime_mod": "gpt-5.6-luna",
  "completion_mod": "gpt-5.6-luna",
  "adversary_mod": "gpt-5.6-luna",
  "coder_intelligence": "xhigh",
  "revision_coder_intelligence": "xhigh",
  "runtime_intelligence": "high",
  "completion_intelligence": "xhigh",
  "adversary_intelligence": "xhigh",
  "speed": "usual",
  "cheap_runtime": true,
  "start_over": false,
  "completion_review": false,
  "adversary": false,
  "max_adversary_runs": 0,
  "max_completion_returns_before_adversary": 0,
  "max_completion_returns_after_adversary": 0,
  "clean": false,
  "protected_path": [],
  "multi_agent": {
    "enabled": false,
    "max_concurrent": 4,
    "default": {
      "model": "gpt-5.6-luna",
      "intelligence": "high"
    },
    "allowed": {
      "gpt-5.6-luna": ["medium", "high", "xhigh"],
      "gpt-5.6-terra": ["medium", "high"]
    }
  },
  "completion_multi_agent": {
    "enabled": false,
    "max_concurrent": 4,
    "default": {
      "model": "gpt-5.6-luna",
      "intelligence": "high"
    },
    "allowed": {
      "gpt-5.6-luna": ["medium", "high", "xhigh"],
      "gpt-5.6-terra": ["medium", "high"]
    }
  },
  "adversary_multi_agent": {
    "enabled": false,
    "max_concurrent": 4,
    "default": {
      "model": "gpt-5.6-luna",
      "intelligence": "high"
    },
    "allowed": {
      "gpt-5.6-luna": ["medium", "high", "xhigh"],
      "gpt-5.6-terra": ["medium", "high"]
    }
  }
}
```

Always include `"review_limit_format": "explicit"`. Without it, older zero-budget semantics are migrated to `"unlimited"`.

## Advisor-supported models and reasoning effort

| Model | Valid effort values | Relative role |
| --- | --- | --- |
| `gpt-5.6-luna` | `low`, `medium`, `high`, `xhigh`, `max` | fast and affordable family |
| `gpt-5.6-terra` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` | balanced family |
| `gpt-5.6-sol` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` | frontier family |
| `gpt-5.5` | `low`, `medium`, `high`, `xhigh` | legacy supported model |

Bello's core parser may preserve a custom nonempty primary-role model ID, but the advisor recommends only the known supported choices above. This is a recommendation-policy boundary, not a claim that every other `ProjectConfig` is syntactically invalid.

All GPT-5.6 variants are eligible for every primary role. In particular, Luna is valid for the initial coder, revision coder, runtime supervisor, completion reviewer, adversary, cheap-runtime triage, and every role's permitted sub-agents. The advisor chooses the full model-effort profile from the task evidence and user objective rather than enforcing a Terra-or-Sol reviewer floor. These schema-valid effort lists are compatibility data, not a capability ranking. Run `scripts/inspect_models.py` for current Codex descriptions and supported efforts before recommending profiles. GPT-5.5 remains a legacy coder choice and is not recommended for runtime, completion, or adversary roles.

Do not treat the local model catalog as a price source. First establish the billing context. For API-key runs, retrieve current official input, cached-input, cache-write, and output token rates; for ChatGPT-authenticated Codex runs, use current plan and credit guidance. These are unit rates, not a total Bello-run price. Use official guidance, the approximate numerical priors, inspected task/repository evidence, and user preferences internally when choosing profiles; do not include that analysis in the advisor output. See [MODEL_ECONOMICS.md](MODEL_ECONOMICS.md).

## Planning stage

Planning is an optional pre-run decision, not a `ProjectConfig` field. Never add `plan` or `plan_path` to the fully resolved JSON.

When a separate plan is recommended, use Codex's built-in Plan Mode to create one advisory Markdown file and pass it at launch with `bello --task TASK.md --plan PLAN.md`. Bello does not create the plan. The initial coder must treat it as a working hypothesis, verify it against the repository, and deviate when implementation reveals facts or nuances the planner could not know. Do not create a replanning loop.

The plan must be a regular `.md` file inside the project root, distinct from the task, not named `AGENTS.md`, not a link or hardlink, and outside Bello runtime, cache, and dependency directories. In a Git repository it must be untracked and absent from reachable Git history. Bello stages a guarded copy for the initial coder, excludes it from the resulting patch, removes it before switching to a revision coder, and keeps completion review, adversary, and adversary-report normalization plan-blind.

## Review scheduler semantics

Runtime supervision is always present. Completion and adversary behavior is controlled by independent switches and three budgets. The following four modes are frequent baselines, not a closed menu:

| Mode | `completion_review` | `adversary` | Returns before A | A passes | Returns after A |
| --- | --- | --- | ---: | ---: | ---: |
| `runtime-only` | `false` | `false` | 0 | 0 | 0 |
| `C` | `true` | `false` | 1 | 0 | 0 |
| `A` | `true` | `true` | 0 | 1 | 0 |
| `C+A` | `true` | `true` | 1 | 1 | 0 |

For `A`, `completion_review: true` is only the controller entry point; the zero return budgets prevent a completion-review stage before or after the adversary. These modes describe bounded opportunities, not guaranteed literal model-call sequences.

The underlying values remain a general scheduler. Select a custom schedule whenever concrete task evidence or an explicit user preference justifies it; there is no need to prove that every baseline fails first. Every additional return or adversary pass should have a distinct reason and an acknowledged time cost.

- With `completion_review: false`, canonicalize `adversary: false` and all three budgets to `0`.
- With `completion_review: true` and `adversary: false`, `max_completion_returns_before_adversary` is the maximum number of completion-review **return decisions** before Bello completes after the coder's next readiness. Set adversary runs and post-adversary returns to `0`.
- With both switches true, `max_completion_returns_before_adversary` bounds completion-review returns before the first adversary. An earlier completion accept starts the adversary immediately; reaching the return limit also starts it without another completion-review call.
- `max_adversary_runs` is the maximum number of adversary passes. It must be positive when adversary is active.
- `max_completion_returns_after_adversary` bounds completion-review returns after each adversary pass. At the limit Bello starts another remaining adversary pass or completes after the final pass. An earlier completion accept advances immediately.
- Every adversary report is separately processed by `adv_report_controller`, using the configured completion model and effort. Its normalization call is not itself one of the completion-return budget units, but it adds cost and time and can return a genuine finding to the coder.

Each return budget accepts any supported non-negative integer or `"unlimited"`; adversary runs accept any non-negative integer. Therefore schedules commonly abbreviated as `2C+A`, `C+A+C`, repeated adversary cycles, and many other combinations are expressible. These abbreviations describe configured opportunities, not a guaranteed literal call sequence: reviewers may accept early, an adversary may find nothing, or a finding may send the coder back into the loop.

A zero pre-adversary budget with a positive adversary budget skips the preceding completion-review call, although `completion_review: true` remains required as the controller entry point. Always keep `"review_limit_format": "explicit"`; otherwise legacy loading can reinterpret zero limits as unlimited.

## Revision-coder semantics

`revision_coder_enabled`, `revision_coder_mod`, and `revision_coder_intelligence` configure an optional one-time profile switch for review-driven repair:

- With `revision_coder_enabled: false`, completion-review and normalized adversary findings are delivered to the current coder thread.
- With `revision_coder_enabled: true`, the first completion-review return or the first finding returned by `adv_report_controller` quiesces the current coder tree and starts one fresh coder thread with the configured revision model and effort. This planned switch is not a health restart and does not consume the health-restart budget. Later reviewer findings and runtime steering reuse that revision thread; Bello does not create a new revision thread for each stage.
- The revision coder works in the same candidate workspace and receives the persisted handoff plus the triggering reviewer feedback. It uses the coder's `multi_agent` policy; there is no separate revision-coder multi-agent object.
- The revision profile is dormant when no reviewer finding is returned, including a runtime-only schedule. Luna, Terra, Sol, and GPT-5.5 remain eligible subject to their supported effort values.

The model and effort fields remain structurally required even while the switch is disabled. When omitted from a sparse saved config, Bello defaults the revision model to the selected coder model and its effort to the selected coder effort.

## Multi-agent invariants

Bello has three independent multi-agent policy objects with the same shape:

- `multi_agent` controls the initial coder and, after a profile switch, the revision coder;
- `completion_multi_agent` controls only completion-review threads;
- `adversary_multi_agent` controls only adversary threads.

For every object, `max_concurrent` is a positive integer. The default child model/effort pair must appear in that object's `allowed` map, and every allowed effort must be valid for its model. Enabling or editing one policy does not change either of the other two.

The advisor owns each role's `enabled` recommendation: it must choose `true` or `false` from the task evidence and user constraints rather than passively preserving the baseline switch. A `false` recommendation still carries a structurally valid child policy, but those child-policy values are dormant.

Coder children may perform bounded implementation or investigation work. Completion-review children may inspect independent requirements, modules, or validation questions, while the parent completion reviewer retains the final accept-or-return judgment. Adversary children may probe independent attack surfaces or failure hypotheses, while the parent adversary retains the final report judgment. Reviewer delegation is one child level deep, and the parent independently verifies relevant child findings.

Runtime supervision and `adv_report_controller` do not have multi-agent policy objects. In particular, `completion_multi_agent` is not used by adversary-report normalization. It is dormant in an adversary-only (`A`) schedule because that schedule has no completion-review call; `adversary_multi_agent` may still be active for its adversary pass.

The conservative default child policy is:

```json
{
  "enabled": true,
  "max_concurrent": 2,
  "default": {
    "model": "gpt-5.6-luna",
    "intelligence": "high"
  },
  "allowed": {
    "gpt-5.6-luna": ["medium", "high", "xhigh"],
    "gpt-5.6-terra": ["medium", "high"]
  }
}
```

For any enabled policy, set `max_concurrent` to the number of named independent workstreams, normally no more than four. Do not add expensive child profiles without a task-specific reason. Child and parent profiles are chosen independently; Luna may be used in either when it is sufficient.

## Task path

The advisor always owns `task` in its returned recommendation. Resolve the current task independently of any saved Bello configuration, require it to be a regular file inside the project root, and emit its normalized project-root-relative path with `/` separators. `task` must never be `null`, empty, absolute, drive-relative, UNC, contain `..`, or retain a temporary-workspace prefix. A nested path such as `tasks/TASK.md` is valid.

The inspector may return `task: null` as a baseline when the saved configuration has no task. Before validating or returning advice, replace that baseline with the current resolved task path. When command execution is allowed, pass both `--project-root` and `--task-file` to `scripts/validate_config.py` so it can verify that the JSON names the exact input file.

## Safe project-field defaults

- `start_over`: emit `false` for advice. It controls Bello history/recovery state and may be changed only when the user explicitly requests it during apply.
- `clean`: emit `false`; use `true` only after the user confirms that this run's workspace is disposable.
- `protected_path`: derive only from an explicit task requirement or user preference; otherwise emit `[]`. Bello denies both reads and writes to these roots, so this is not a read-only-file mechanism. Do not add the task file, whose integrity Bello already checks, or a reference executable that the task requires the coder to use.
- `speed`: use `usual`; `fast` is a latency choice, not a cost-saving choice. It applies to coder, revision-coder, runtime-supervisor, and completion-review turns, but not adversary turns.

`cheap_runtime` is a Boolean. When enabled, Bello internally uses cheap triage for routine observations. In Bello 0.5.0 its default model is GPT-5.6 Luna; advanced users can override only the model through `BELLO_RUNTIME_TRIAGE_MODEL`. The project config and CLI expose neither a separate cheap-runtime model nor a separate effort, and the cheap-runtime request does not set an explicit effort. Do not describe it as `xhigh` or claim a fixed effort.

## Current application limitation

The current run CLI exposes initial-coder, runtime, completion, and adversary models and efforts; review/adversary toggles; adversary count; speed; task; an optional private `--plan PATH`; start-over; clean; and protected paths. These one-run flags override the corresponding saved values without rewriting the project config. `--plan` has no persistent config counterpart and applies only to that run.

It does not expose revision-coder enablement/model/effort, cheap runtime, completion-return budgets, or any of the three multi-agent policy objects as one-run flags. Those fields require the saved `bello config` interface. A one-run initial-coder override does not implicitly rewrite the persisted revision-coder profile.

The older `bello-delegate` plugin may still refer to paired `--super-mod` settings and efforts only through `xhigh`. Do not flatten a modern recommendation to that older interface or silently omit independent role settings.
