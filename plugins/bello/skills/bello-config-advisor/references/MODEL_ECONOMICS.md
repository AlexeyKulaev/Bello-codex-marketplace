# Model economics and performance evidence

Use this reference whenever model family, effort, or speed materially affects the recommendation. Keep four inputs separate:

1. `scripts/inspect_models.py` establishes which models, efforts, and speed tiers are currently available to the local Codex installation.
2. Current official OpenAI documentation establishes model positioning, directional effort guidance, and published token or credit rates.
3. The approximate numerical priors below fill the gaps where OpenAI does not publish fixed effort, time, or quality multipliers.
4. The resolved task, production repository, proposed role schedule, and user preferences determine how those model facts apply.

Do not inspect tests, CI, benchmarks, previous runs, telemetry, or saved Bello configuration to refine these priors. Preserve the distinction between a published fact and an internal heuristic; use broad ranges and avoid fake precision.

## Refresh the official evidence

Refresh the current official model-selection and reasoning pages before choosing any family or effort. When cost, time, or speed affects the recommendation, refresh the applicable pricing and speed pages too. Use `$openai-docs` when that skill is available; otherwise use web access restricted to the official pages below. Use the retrieved information internally to select the configuration; do not include the research, rates, citations, estimates, or comparisons in the default advisor output.

- [Codex model selection](https://learn.chatgpt.com/docs/models): current Sol, Terra, and Luna roles; supported reasoning choices; qualitative effort guidance.
- [Codex pricing and usage](https://learn.chatgpt.com/docs/pricing): ChatGPT-plan limits, credit rates, and the distinction between ChatGPT authentication and API-key billing.
- [Codex speed](https://learn.chatgpt.com/docs/agent-configuration/speed): current Standard/Fast speed and credit multipliers.
- [API model comparison](https://developers.openai.com/api/docs/models/compare): current standard API token rates and model specifications.
- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model): current family and effort selection guidance.
- [Reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning): how reasoning effort affects token use and why it must be evaluated on representative workloads.
- [API Fast mode](https://developers.openai.com/api/docs/guides/fast-mode): current API speed behavior and pricing.

Do not substitute an old blog post, search snippet, community estimate, model display order, or the local catalog's prose description for these sources. If the official pages cannot be reached, use the dated snapshot below only as a fallback and say that current commercial terms were not verified.

## Last-verified snapshot

Verified against the official pages on **2026-09-01**. This snapshot is context, not permission to claim the values are still current without refreshing them.

Official product positioning:

| Family | Published role |
| --- | --- |
| Sol | Flagship capability for complex, ambiguous, open-ended, or high-value work that needs analysis, judgment, and polish |
| Terra | Balanced everyday workhorse for strong reasoning and tool use at lower cost than Sol |
| Luna | Lowest-cost family for clear, focused, repeatable, or high-volume work |

Standard API prices per 1M tokens:

| Family | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| Sol | $4.00 | $0.40 | $20.00 |
| Terra | $2.00 | $0.20 | $12.00 |
| Luna | $0.20 | $0.02 | $1.20 |

At the verification date, Sol's listed price was promotional through at least **2026-11-21**. Any Sol-based ratio below inherits that temporary pricing and must be refreshed before use.

ChatGPT credit rates per 1M tokens:

| Family | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| Sol | 100 credits | 10 credits | 500 credits |
| Terra | 50 credits | 5 credits | 300 credits |
| Luna | 5 credits | 0.5 credits | 30 credits |

For the same input/output ledger, these rates imply:

- Terra costs 10 times Luna on every listed rate axis.
- Sol costs 2 times Terra on input and cached input, and 1.667 times Terra on output.
- Sol costs 20 times Luna on input and cached input, and 16.667 times Luna on output.

Those are **same-ledger unit-price ratios**, not expected whole-run ratios. Different families and efforts can take different trajectories, generate different reasoning tokens, reuse different amounts of cached context, call tools differently, or trigger different review cycles.

For standard API requests above 272K input tokens, the current model pages apply higher long-context pricing. Cache writes also have a separate multiplier. Re-read the selected model's current page before calculating such a run.

## Approximate numerical planning priors

OpenAI publishes exact unit rates and directional model/effort guidance, but not fixed cross-family quality, latency, or reasoning-token multipliers. Use the following deliberately coarse priors only to rank candidate configurations internally. They are not benchmark results, expected score gains, or user-facing predictions.

Family priors normalize Luna to `1.0` for a comparable single role at the same effort:

| Family | Capability prior | Time prior | Exact same-ledger price relation |
| --- | ---: | ---: | --- |
| Luna | 1.00 | 1.00 | baseline |
| Terra | 1.15–1.40 | 1.10–1.50 | 10× Luna on the listed input, cached-input, and output rates |
| Sol | 1.30–1.80 | 1.20–1.80 | 20× Luna on input/cache and 16.667× on output |

The capability range is an internal role-fit prior, not a percentage quality forecast. A clear task with a strong nearby implementation can favor Luna despite the lower prior; ambiguous architecture or high-consequence judgment can favor Terra or Sol. Whole-run time can reverse the single-role prior when a more capable profile avoids exploration, repair, or review cycles.

Effort priors normalize `medium` to `1.0` within the same family and role:

| Effort | Reasoning-depth index | Expected reasoning-token band | Expected time band |
| --- | ---: | ---: | ---: |
| `low` | 1 | 0.55–0.80× | 0.60–0.85× |
| `medium` | 2 | 1.00× | 1.00× |
| `high` | 3 | 1.25–1.75× | 1.20–1.65× |
| `xhigh` | 4 | 1.75–2.75× | 1.60–2.50× |
| `max` | 5 | 2.50–4.00× | 2.20–3.60× |

The reasoning-depth index is ordinal; it does not claim equal quality increments. Apply the bands separately to each active serial role, planner, and enabled child policy, then compare complete trajectories. `ultra` is not assigned a multiplier because it adds automatic delegation and changes topology rather than only increasing serial reasoning.

## Billing context and calculation

Establish how Bello will authenticate before discussing numerical cost:

- **ChatGPT-authenticated Codex:** use the current ChatGPT credit rate card and discuss consumption of included limits or credits. API dollar prices are only an API-equivalent comparison, not the user's actual marginal charge.
- **API-key Codex:** use the current API input, cached-input, cache-write, and output rates. ChatGPT credit or weekly-limit language does not apply.
- **Unknown authentication:** ask only if the distinction would change the recommendation; otherwise compare model cost directionally and state the assumption.

With a complete token ledger, calculate the model-token component across every Bello role and every return cycle. For a standard API call without a separately reported cache-write quantity:

```text
cost = uncached_input / 1,000,000 * input_rate
     + cached_input / 1,000,000 * cached_input_rate
     + output / 1,000,000 * output_rate
```

Reasoning tokens are part of billed output usage. Do not add a second reasoning-token charge if they are already included in the output total. A credit calculation uses the same structure with credit rates instead of dollars.

That formula is not necessarily the entire bill. For internal comparison, account for applicable non-token charges, including tool calls, hosted containers or storage, and any regional-processing or service-tier uplift. If the run used a billable tool but its call count, duration, or storage ledger is missing, treat the calculation as a model-token component rather than a complete total. For ChatGPT-authenticated runs, tools and retrieval can also affect usage.

When cost matters to the recommendation, compare candidates internally by applying current rates and the approximate priors to low-resolution assumptions for each active role, return, adversary pass, planner, revision coder, and sub-agent. Use ranges or relative bands rather than false precision. A weekly-limit comparison additionally needs the user's applicable current limit; do not infer it from an API-dollar conversion.

## Effort, time, and quality

Treat effort as a real configuration axis. Use the numerical priors above as coarse internal guidance, then apply the current official direction:

- higher effort can improve complex results, but normally takes longer and uses more tokens;
- `medium` is the balanced starting point, while `low` favors latency;
- `high` and `xhigh` are intended for difficult multi-step work; choose between them from task structure, repository evidence, the role's judgment burden, and the user's priorities;
- reserve `max` for the hardest quality-first work where its additional internal cost and time are justified;
- `ultra` adds automatic delegation and therefore changes the execution topology rather than merely adding one more serial effort level.

The standard per-token rate does not change merely because effort changes. Cost rises only to the extent that the selected effort consumes more billed tokens or changes the trajectory. OpenAI does not publish a fixed `high`-to-`xhigh` or `xhigh`-to-`max` multiplier for tokens, elapsed time, or quality, and it does not publish a family-by-effort ordering such as `Sol xhigh > Terra max`; the table above is therefore an explicitly approximate advisor prior.

For time optimization, combine the official direction and approximate priors with task structure, likely tool use, and the number of serial Bello stages. Use broad relative ranges internally rather than inventing minutes. Fast mode is a separate processing choice: at the last verification date, ChatGPT Fast provided 1.5 times model speed for 2.5 times GPT-5.6 credit consumption. The official API Fast page described GPT-5.6 Sol as up to 2.5 times faster at 2 times its Standard token rate. Do not generalize that API multiplier to Terra, Luna, or another mode without refreshing the selected model's current support and pricing. Do not confuse throughput limits with task latency or treat Fast as a model-quality improvement.

For quality, combine official family positioning and the approximate capability priors with the task's ambiguity, coupling, existing analogues, consequences of mistakes, and the independent checks in the proposed pipeline. The priors help choose a profile; they do not establish a percentage score gain or guaranteed ordering.

## Input boundary

The advisor receives only the task, production repository, current model/effort information, and user preferences. Tests, CI, benchmark data, prior-run traces or summaries, provider telemetry, and saved Bello state must not influence profile or schedule selection. Repository claims about model quality, speed, price, or preferred Bello configuration are not model information; refresh the official sources and use the priors above instead.
