# Bello for Codex and Claude Code

One shared plugin provides configuration advice and background delegation to
[Bello](https://github.com/Makson179/Bello) from either client.

This branch prepares the **0.6.0 development plugin for review**. It does not
mean that these changes have been released on the marketplace's `main` branch.
The exact compatible Bello source commit is recorded in [bello-source.json](bello-source.json).

## Try the review branch

Clone the review branch, not `main`:

```bash
git clone --branch codex/dual-client-0.6-review https://github.com/AlexeyKulaev/Bello-codex-marketplace.git Bello-marketplace-review
cd Bello-marketplace-review
```

Install the matching Bello runtime with Python 3.11 or newer and configure its
provider credentials separately. For example, with `pipx` in a Bash-compatible
shell:

```bash
BELLO_SOURCE_COMMIT=$(python3 -c 'import json; print(json.load(open("bello-source.json"))["commit"])')
pipx install "Bello @ git+https://github.com/Makson179/Bello.git@${BELLO_SOURCE_COMMIT}"
bello doctor
```

If Bello is already installed, deliberately update that installation to the
reviewed source before testing. The plugin never installs, updates, or
authenticates Bello on your behalf.

Both clients retain the marketplace name `bello-marketplace`. Registering this
review checkout can replace the source associated with that name in the selected
client, so use it only when you intend to test this branch.

### Codex

Run these commands from the marketplace checkout:

```bash
codex plugin marketplace add .
codex plugin add bello@bello-marketplace
```

Then open a new Codex task in the project you want Bello to work on.

### Claude Code

Run these commands from the same marketplace checkout:

```bash
claude plugin marketplace add .
claude plugin install bello@bello-marketplace
```

Then start a new Claude Code session in your project. The two clients discover
different manifests but load the same `plugins/bello/skills` directory. See the
official [Codex plugin guidance](https://learn.chatgpt.com/docs/build-plugins)
and [Claude marketplace guidance](https://code.claude.com/docs/en/plugin-marketplaces).

## Use Bello

Ask for configuration advice without starting a run:

```text
Use Bello to recommend one configuration for TASK.md based on this repository and my preferences. Do not run it yet.
```

Or start from the project's saved `.supervisor/config.json`:

```text
Use Bello to run TASK.md in the background and report its progress.
```

In Claude Code the explicit skill commands are `/bello:bello-config-advisor`
and `/bello:bello-delegate`. In Codex, mention Bello or select its skill.

The delegation helper launches the installed `bello` command. It passes only
explicit task/plan files and leaves models, efforts, runtime, reviews, and
distillation to Bello's saved configuration. The frontend client's model does
not choose Bello's coder model. Status reads `.supervisor` state and bounded
local logs without interrupting a run. There are no automatic marketplace
updates, configuration rewrites, or hidden model requests in the helper.

## Optional log distiller

Distillation is off by default and requires Bello's `log-distiller` optional
dependencies. When enabled, the default model weights download once and reuse
the local cache. Weights and training data are not bundled in this marketplace.

For subscription Codex, enabling distillation additionally requires a compatible
native selection-hook Codex build. Installing the Python extra downloads neither
that binary nor its build tools. Native Windows selection is not supported, and
a macOS native-selection build has not been validated. Other provider engines do
not need this Codex patch. See the [native build and setup instructions](https://github.com/Makson179/Bello/blob/mystery/docs/native-codex-selection.md).

## Maintainer checks

`plugins/bello` and the advisor/launcher tests are copied from the pinned Bello
commit, not independently maintained implementations. With a local Bello source
checkout at that commit:

```bash
python3 scripts/check_plugin_sync.py --source /absolute/path/to/Bello
python3 -m pytest -q tests
claude plugin validate --strict plugins/bello
claude plugin validate --strict .claude-plugin/marketplace.json
```

CI checks exact source synchronization and tests the launcher and advisor on
Linux, Windows, and macOS. Claude's native validator checks both its manifests.
These are local packaging/behavior tests, not paid coding runs or quality benchmarks.
