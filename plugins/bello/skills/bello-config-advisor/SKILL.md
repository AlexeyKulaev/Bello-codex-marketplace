---
name: bello-config-advisor
description: Inspect a coding task, workspace, and user constraints, then recommend one concrete Bello configuration and decide whether a separate planning pass should precede execution. Use when a user asks Codex to choose or optimize a Bello configuration before a run. Do not use merely to monitor a run whose configuration is already fixed.
---

# Bello Config Advisor

Turn exactly four inputs—the resolved task file, the production repository, current OpenAI model/effort information, and the user's quality, cost, and time preferences—into one usable Bello configuration. Also decide whether a separate planning profile should first prepare an advisory plan for the executor. If the user gives no preference, favor the least expensive setup that still has strong expected quality.

Advice is read-only by default. Do not start Bello, edit `.supervisor/config.json`, or change project files unless the user separately asks to configure or run the task.

## Inspect

1. Read [SELECTION_POLICY.md](references/SELECTION_POLICY.md) completely. Read [CONFIG_SCHEMA.md](references/CONFIG_SCHEMA.md) before emitting exact config JSON, and use [OUTPUT_CONTRACT.md](references/OUTPUT_CONTRACT.md) for the response.
2. Run `scripts/inspect_models.py` before choosing profiles. Use it only to establish the current local models, supported effort values, and speed tiers. If the current catalog cannot be retrieved, use its bundled fallback and mark availability accordingly.
3. Read [MODEL_ECONOMICS.md](references/MODEL_ECONOMICS.md) before choosing any model-effort profile. Refresh its official OpenAI model-selection and reasoning guidance for every recommendation; when cost, time, or speed matters, also refresh the linked pricing and speed pages. Establish whether the run uses ChatGPT limits/credits or API-key token billing. Use published model rates and the documented approximate numerical priors only for internal selection.
4. Resolve the project root and the task file. The task must be a regular file inside the project root. In the returned config, set `task` to that file's normalized project-root-relative path with `/` separators; never emit `null`, an absolute path, `..`, or a temporary-workspace prefix.
5. Inspect only the task and task-relevant production repository files: applicable workspace instructions, manifests, source layout, interfaces, data flows, nearby implementations, and the current diff where useful. Existing implementations of a similar command, adapter, data flow, or subsystem are important evidence because they can constrain the intended architecture and make a cheaper executor sufficient. Use `rg --files` or `git ls-files` before broader traversal. Ignore tests and test directories, CI configuration and results, benchmark artifacts, prior runs, run telemetry, hidden `.supervisor` history, and saved Bello configuration when choosing the setup. A testing requirement written in the task remains part of the task; the existing test suite is not a separate input.
6. Extract the user's hard constraints and softer wishes, including requests such as cheaper, highest practical quality, faster, no sub-agents, or a specific review schedule. Ask one focused question only when an unanswered constraint would materially change the recommendation; otherwise state the assumption and continue.
7. Do not inspect the saved Bello configuration while selecting a recommendation. Run `scripts/inspect_config.py` only after the user asks to apply or launch the already selected setup, and use it only for compatibility, liveness, and safe preservation of runtime-owned state.
8. Do not run tests, builds, installers, the task's code, plain `bello`, configuration editors, or plugin update scripts merely to recommend a setup.

## Choose

- Decide first whether a separate planning pass materially improves the quality/cost tradeoff. Recommend one only when task-wide architecture, coupled requirements, or sequencing can be resolved meaningfully before implementation and the expected reduction in execution work or risk repays the planning call's own cost and time. When planning is selected, the planner's expected task-relevant capability must be at least as high as the initial coder's; never weaken the planner to save cost or time. Within one family, use the coder's effort or a higher one. Across families, use a different planner only when current evidence makes its non-inferiority defensible; if the ordering is uncertain, use the exact coder profile or a clearly stronger same-family profile for planning. Compare planner and executor as complete model-effort profiles; do not call one stronger merely because it uses Sol, or because its family differs. Use Codex's built-in Plan Mode, produce one advisory Markdown plan, and do not create a replanning loop. The executor must verify the plan against the repository and may deviate when implementation reveals facts or nuances the planner could not know. Planning is a pre-run decision, not a `ProjectConfig` field.
- Choose the initial coder model and effort for forming or executing the solution. Without a plan it must be capable enough to discover the architecture without relying on a later rescue. With a plan it may use a lower-unit-price profile than the planner, but it must still be capable of checking the plan's assumptions and adapting it. Make an explicit revision-coder yes/no decision for every recommendation. Enable the switch only when an active review stage can return work, concrete bounded repairs are plausible, and expected savings across correction cycles repay the fresh-thread handoff. Do not recommend a revision profile as a capability upgrade over the initial coder; use the same or a cheaper sufficient profile, or leave revision disabled when repairs may require the initial coder's reasoning and context.
- Treat model family and effort as independent axes. Sol is the frontier coding family, Terra balances capability and cost, and Luna emphasizes speed and affordability; effort controls how much reasoning, exploration, and verification the selected family performs. Do not invent a guaranteed total capability order for cross-family pairs such as `Sol xhigh` and `Terra max`; choose from role fit, current prices, approximate time/reasoning priors, the task, the repository, and the user's preference.
- Choose runtime, completion, and adversary parents independently. Luna, Terra, and Sol are all eligible for every primary role; choose the least expensive full model-effort profile sufficient for that role's actual judgment rather than applying a model-family floor.
- Treat `runtime-only`, `C`, `A`, and `C+A` as frequent starting points, not as a closed menu. Use any supported schedule, including `2C+A`, `C+A+C`, or repeated adversary passes, when task evidence or the user's wishes justify its additional serial cost and time.
- Decide coder, completion-reviewer, and adversary multi-agent policies separately. Sub-agents may help with independent implementation work, repository investigation, requirement audits, or adversarial probes; they do not require multiple file-parallel implementation streams. For every enabled role, choose exact concurrency, default child profile, and allowed model-effort pool. Reviewer children may use the cheapest sufficient allowed profiles, while the parent retains final judgment and owns the report.
- Compare expected quality, whole-trajectory cost, and time. Count an optional planning pass, completion calls, adversary passes, report normalization, coder returns, context/thread changes, repeated validation, and sub-agent coordination as possible costs. A cheap model does not guarantee a cheap or fast run.

Do not assign a difficulty label to the task or its dimensions. Base the choice only on the resolved task, the production repository, current OpenAI model/effort information, and the user's preferences. Do not use tests, CI, benchmark scores, prior-run outcomes, telemetry, or a saved Bello configuration as selection evidence even when those artifacts are present. Use the approximate numerical priors only to compare candidate configurations internally; never present them as measured outcomes or guarantees.

## Report

Follow [OUTPUT_CONTRACT.md](references/OUTPUT_CONTRACT.md). Return only:

1. one minimal planning parameter line: `Plan: none` or `Plan: MODEL EFFORT -> PLAN.md`;
2. one fully resolved, ready-to-use Bello config JSON object.

Do not expose the internal selection process. Do not add rationale, task analysis, alternatives, estimates, model comparisons, prices, time predictions, quality predictions, confidence, source links, citations, validation narration, headings, or a machine-readable advice wrapper. Planning stays outside the config JSON because `--plan` is a run-only input rather than project configuration.

Validate the selected JSON silently against [CONFIG_SCHEMA.md](references/CONFIG_SCHEMA.md) and `scripts/validate_config.py`. When command execution is allowed, run the validator with both `--project-root` and `--task-file` so it checks the exact relative task path; if the user forbids commands, check the documented invariants and validator source manually. If validation or a checked installation reveals an incompatibility, return only the concise blocker instead of silently dropping revision-coder or reviewer multi-agent settings or emitting an invalid config.

## Apply only when asked

When the user asks to apply or run the recommendation:

- run the inspector with the optional Bello version check and require a clear apply guard; do not revise the selected profiles from saved configuration;
- for an uncertain guard, recheck process liveness or ask for confirmation rather than treating stale state as safe;
- if planning was recommended, prepare exactly one advisory Markdown plan with the recommended planner profile before launch. The plan must be a regular file inside the project, distinct from the task, not named `AGENTS.md`, untracked, and absent from reachable Git history. Do not start a replanning loop;
- do not overwrite `.supervisor/config.json` directly, especially during an active run;
- use Bello's supported configuration interface and preserve fields outside the recommendation's scope;
- set `task` to the resolved project-root-relative task path; preserve `start_over` and `protected_path`; use `clean: true` or unbounded review budgets only after explicit confirmation;
- show the planning decision and resolved config before launch, pass the prepared plan with `--plan`, and report any field the installed interface cannot express.
