# Bello Command Order

When constructing Bello commands, preserve this order:

1. Main command:

   `bello`

2. Subcommands:

   `doctor`
   `update`

3. Version/help flags:

   `--version`
   `-V`
   `--help`
   `-h`

4. Run options:

   `--task TASK.md`
   `--coder-mod MODEL`
   `--super-mod MODEL`
   `--coder-intelligence low|medium|high|xhigh`
   `--super-intelligence low|medium|high|xhigh`
   `--fast[=true|false]`
   `--start-over[=true|false]`
   `--clean[=true|false]`
   `--completion-review[=true|false]`
   `--adversary[=true|false]`
   `--adversary-runs N`
   `--protected-path PATH`

Rules:

- Preserve user-provided parameters.
- Do not invent model names.
- `--coder-mod` must be used together with `--super-mod`.
- `--super-mod` must be used together with `--coder-mod`.
- `--clean` must be used only when the user explicitly requests it.
- `--model` is not a current Bello flag; use paired `--coder-mod` and `--super-mod`.
- `--protected-path PATH` may be repeated.
- Unknown arguments must be rejected instead of silently forwarded.
