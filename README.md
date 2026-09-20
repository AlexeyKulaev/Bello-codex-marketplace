# Bello for Codex and Claude Code

One shared plugin provides configuration advice and background delegation to
[Bello](https://github.com/Makson179/Bello) from either client.

This marketplace provides the **0.6.0 plugin** for both clients.
The exact compatible Bello source commit is recorded in [bello-source.json](bello-source.json).

## Install

Clone the stable marketplace branch:

```bash
git clone --branch main https://github.com/AlexeyKulaev/Bello-codex-marketplace.git Bello-marketplace
cd Bello-marketplace
```

Install Bello 0.6.0 with Python 3.11 or newer and configure its provider
credentials separately. For example, with `pipx`:

```bash
pipx install "Bello==0.6.0"
bello doctor
```

If Bello is already installed, update it to 0.6.0 before using this plugin.
The plugin never installs, updates, or authenticates Bello on your behalf.

Both clients use the marketplace name `bello-marketplace`.

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
native selection-hook Codex build. Bello downloads and verifies the pinned build
automatically on macOS Apple Silicon, Windows x86_64, and Linux x86_64
(glibc 2.35+) when needed. Installing the Python extra alone does not download
the binary or its build tools. Other provider engines do not
need this Codex patch. See `docs/native-codex-selection.md` in the Bello source
commit recorded in [bello-source.json](bello-source.json).

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
