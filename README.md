# Bello for Codex

## Installation

Install Bello:

```bash 
pipx install bello
bello doctor
```

## Add Codex Marketplace

```bash
codex plugin marketplace add AlexeyKulaev/Bello-codex-marketplace --ref main
```

## Install Plugin

```bash
codex plugin add bello@bello-marketplace
```

Alternatively, open Codex:
  
```bash
codex
/plugins
```

Then install **Bello** from the plugin list.

## Usage

In a project directory, create a task file:

```bash
cat > TASK.md <<'EOF'
Create hello.py that prints "hello from bello".
Run python3 hello.py to validate it.
EOF
```

Then run Bello in Codex:

```text
@Bello run TASK.md with --start-over and keep me updated
```

To have Codex inspect the task and choose a cost-efficient configuration first:

```text
@Bello choose the cheapest defensible configuration for TASK.md. Do not run it yet.
```

The config advisor reads the task, project, and your quality, cost, and time
preferences. It chooses role models, review budgets, adversary passes, runtime
supervision, and useful parallelism independently. It also decides whether one
strong planning pass can make a cheaper executor viable, then returns one fully
resolved recommendation. Advice is read-only unless you also ask Codex to apply
the configuration or run the task.

## How the Plugin Works

The plugin:

* inspects a coding task and recommends one Bello configuration for the requested quality, cost, and time tradeoff;
* checks whether the Codex plugin marketplace is behind `main`;
* automatically refreshes and reinstalls the plugin when a newer commit exists, with retries and recovery commands on failure;
* checks `bello doctor`;
* checks `bello --version`;
* runs `bello update` when an update is available;
* starts `bello --task TASK.md ...`;
* monitors `.supervisor/` state files;
* reports progress in Codex;
* summarizes `.supervisor/FINAL_REPORT.md` and `git diff`.

Bello itself controls Codex through:

```bash
codex app-server --listen stdio://
```

using JSON-RPC.

During an active run, the plugin monitors Bello's state and reports progress;
Bello itself owns the JSON-RPC control loop with Codex.

## Update

Update the Bello binary:

```bash
bello update
bello doctor
```

The delegation workflow checks for plugin updates before each Bello run. The
read-only config advisor does not mutate the installed plugin while evaluating
a task. The delegation update check
compares the configured `bello-marketplace` snapshot commit with the latest
commit on `refs/heads/main`. If the Git remote is unreachable, the plugin logs
that the check was skipped and continues with the installed version. If the
commit hashes differ, it refreshes the marketplace, verifies the plugin
manifest, removes the installed plugin, and reinstalls it with bounded retries:

```bash
codex plugin marketplace upgrade bello-marketplace
codex plugin remove bello@bello-marketplace
codex plugin add bello@bello-marketplace
```

If reinstall fails after removal, the script prints manual recovery commands
and stops before starting Bello.

After an automatic plugin update, start a new Codex thread or rerun the request
so Codex loads the updated skill bundle.

Manual fallback:

```bash
codex plugin marketplace upgrade bello-marketplace
codex plugin remove bello@bello-marketplace
codex plugin add bello@bello-marketplace
```

If you only need to retry the install step:

```bash
codex plugin remove bello@bello-marketplace
codex plugin add bello@bello-marketplace
```

For every published plugin release, bump
`plugins/bello/.codex-plugin/plugin.json` `version`; Codex caches
installed plugin bundles by plugin identity and version.
