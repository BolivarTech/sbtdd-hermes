# SBTDD-Hermes — Spec + Behavior + TDD Plugin for Hermes Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Hermes](https://img.shields.io/badge/hermes-compatible-green.svg)](https://hermes-agent.nousresearch.com/docs)

A **Hermes Agent plugin** implementing **SBTDD** (Spec + Behavior + Test Driven Development) — a structured workflow that forces five gates before a single line of production code is committed.

Ported from the Claude superpowers ecosystem to Hermes native plugin architecture with `pre_tool_call` hooks, slash commands, and agent tools. Includes automatic TDD-Guard enforcement, MAGI integration for adversarial review, and pre-merge dual-loop verification.

Forked from the original [SBTDD-Skill](https://github.com/BolivarTech/SBTDD-Skill) and the [Claude superpowers workflow](https://github.com/BolivarTech/ai-workflows).

---

## Why SBTDD?

Single-pass coding produces brittle code. SBTDD forces explicit specification, planning, review, and verification before implementation:

1. **Specification** — Define behavior with Given/When/Then scenarios
2. **Planning** — Generate a TDD task plan with checkpoints
3. **MAGI Review** — Three adversarial agents challenge the plan (§6 gate)
4. **TDD Execution** — Red → Green → Refactor with automatic tool interception
5. **Pre-Merge Verification** — Automated + MAGI dual-loop review

### How It Differs from the Original (Claude)

| Feature | Claude Skill | This Hermes Plugin |
|---------|-------------|-------------------|
| Registration | `CLAUDE.md` + `settings.json` | Native `hermes_agent.plugins` entry-point |
| Commands | Superpowers `/sbtdd` | Slash commands `/sbtdd`, `/sbtdd-init`, `/sbtdd-check` |
| Tools | N/A | `sbtdd_status`, `sbtdd_update_state` |
| Hooks | `PreToolUse` (external) | Native `pre_tool_call`, `on_session_start` |
| TDD-Guard | External binary | Native hook with override budget |
| State | `.claude/state.json` | `.hermes/session-state.json` (OCC + filelock) |
| MAGI Review | `/skill magi` | Same — MAGI is a separate Hermes plugin |
| Backend | Anthropic only | Hermes Agent (any provider) |

---

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com/) installed
- Python 3.11+
- Optional: [MAGI-Hermes plugin](https://github.com/BolivarTech/MAGI-Hermes) for adversarial review gates

---

## Installation

Hermes uses a **directory plugin** system. The standard Hermes installer runs from a stripped virtual environment without `pip`, so the `pyproject.toml` entry-point is reserved for advanced users running Hermes from source. The method below works for all standard installations.

### Step 1 — Clone the repository

```bash
git clone https://github.com/BolivarTech/sbtdd-hermes.git
cd sbtdd-hermes
```

### Step 2 — Install as a directory plugin

Hermes looks for plugins under `~/.hermes/plugins/<name>/`. The path `~/.hermes` expands automatically on every OS (Linux/macOS: `$HOME/.hermes`, Windows: `%USERPROFILE%\AppData\Local\hermes`).

```bash
# Create the plugin directory
mkdir -p ~/.hermes/plugins/sbtdd

# Copy the entire repo contents (preserves the sbtdd_hermes/ package)
cp -r . ~/.hermes/plugins/sbtdd/
```

> **Tip:** On Windows PowerShell the same command is:
> ```powershell
> $pluginsDir = "$env:USERPROFILE\AppData\Local\hermes\plugins\sbtdd"
> New-Item -ItemType Directory -Force -Path $pluginsDir
> Copy-Item -Path "$(Get-Location)\*" -Destination $pluginsDir -Recurse -Force
> ```

After copying, `~/.hermes/plugins/sbtdd/` should contain:

```
~/.hermes/plugins/sbtdd/
├── __init__.py              # delegates to sbtdd_hermes.register()
├── plugin.yaml              # Hermes plugin manifest
├── pyproject.toml           # optional build metadata
├── README.md
├── LICENSE
├── LICENSE-APACHE
├── sbtdd_hermes/            # implementation package
│   ├── __init__.py            # register(ctx) + hooks + state cache
│   ├── commands.py            # Slash command handlers
│   ├── state.py               # SessionState + OCC + filelock
│   ├── validator.py           # Field validation + cross-field checks
│   ├── magi_parser.py         # MAGI report parser with timeout
│   ├── _config.py             # Constants + state machine
│   ├── prompts.py             # Prompt generators
│   ├── scaffolding.py         # Init logic
│   ├── py.typed               # PEP 561 marker
│   └── scripts/               # Verification runners
│       ├── verify.py
│       ├── git_status.py
│       ├── drift_check.py
│       └── commit_helper.py
├── templates/               # HERMES.local.md, verification per stack
├── references/              # Guides for LLM
└── tests/                   # Test suite
```

> **How it works:** Hermes imports the root `__init__.py`, which calls `sbtdd_hermes.register(ctx)`. The package uses relative imports, so it resolves correctly both as a directory plugin and via pip.

### Step 3 — Enable the plugin

Hermes is **opt-in**: only plugins listed in `plugins.enabled` are loaded.

Run **outside** Hermes (in your regular shell):

```bash
hermes plugins enable sbtdd
```

Or edit `~/.hermes/config.yaml` manually and ensure `enabled` is a **YAML list**, not a string:

```yaml
plugins:
  enabled:
    - sbtdd
```

> **Common mistake:** `hermes config set plugins.enabled "[sbtdd]"` writes the string literal `enabled: '[sbtdd]'`, which Hermes ignores. Always use `hermes plugins enable sbtdd` or a proper YAML list.

### Step 4 — Restart Hermes

Plugin discovery runs **once at startup**.

```bash
exit    # or /exit if you are inside Hermes
hermes  # start Hermes again
```

### Step 5 — Verify

Inside Hermes:

```bash
/plugins
```

Expected output:

```
User plugins (1):
  ● sbtdd v2.0.1 [enabled]
```

If it shows `[not enabled] — not enabled in config`, run `hermes plugins enable sbtdd` **outside** Hermes and restart again.

---

### Updating the plugin

Pull the latest changes and re-copy:

```bash
cd sbtdd-hermes
git pull

# Re-install
cp -r . ~/.hermes/plugins/sbtdd/
```

> **Tip:** On Windows PowerShell the same command is:
> ```powershell
> cd sbtdd-hermes
> git pull
> $pluginsDir = "$env:USERPROFILE\AppData\Local\hermes\plugins\sbtdd"
> Copy-Item -Path "$(Get-Location)\*" -Destination $pluginsDir -Recurse -Force
> ```

Then restart Hermes (`exit` + `hermes`).

---

### Advanced: pip install (source builds only)

This method is **only for developers who build Hermes from source** using a shared Python virtual environment. It does NOT work with the standard Hermes installer.

#### When does this apply?

| Scenario | Method to use |
|----------|--------------|
| Standard Hermes installer (most users) | Directory plugin (see Step 2 above) |
| Running Hermes from Git source (`python -m hermes_agent`) | `pip install -e .` |
| Developing Hermes core itself | `pip install -e .` |
| Hermes installed via `uv tool install` or `pipx` | Directory plugin only |

The standard Hermes installer bundles its own isolated, stripped virtual environment. That venv **lacks pip, setuptools and importlib.metadata**, so any package you install with `pip` elsewhere on your system is invisible to it.

#### How to check which scenario you are in

```bash
# Run this outside Hermes
python -c "import hermes_agent; print(hermes_agent.__file__)"
```

- If it prints a path inside `site-packages` of your **own** venv → you have a source/shared install → `pip install -e .` works.
- If the command fails with `ModuleNotFoundError` → you have the standard installer → **use the directory plugin**.

#### If you are in the source-build scenario

```bash
# Activate the SAME venv where Hermes itself is installed
source /path/to/hermes-venv/bin/activate

# Install SBTDD plugin in editable mode
cd sbtdd-hermes
pip install -e .
```

Hermes will auto-discover the plugin via the `pyproject.toml` entry-point on next startup. Then enable and restart as usual.

> **Never mix methods.** If you install via `pip` AND copy as directory plugin, Hermes may load duplicate registrations. Pick one.

---

## Configuration

SBTDD stores its configuration in two places:

### Session state file

`.hermes/session-state.json` — created automatically on first `/sbtdd-init`, gitignored:

```json
{
  "schema_version": 1,
  "state_revision": 0,
  "plan_path": "planning/hermes-plan-tdd.md",
  "current_task_id": null,
  "current_task_title": null,
  "current_phase": "red",
  "magi_backend": "ollama",
  "magi_iterations_used": 0,
  "magi_iteration_budget": null
}
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SBTDD_STRICT` | `"false"` | If `"true"`, fail on corrupted state instead of fallback to defaults |
| `OLLAMA_HOST` | `http://localhost:11434/v1` | MAGI backend endpoint (only if using MAGI) |

### Hermes config.yaml (optional)

```bash
hermes config set sbtdd.magi_backend ollama
hermes config set sbtdd.strict false
```

---

## Usage

### Slash commands

```bash
/sbtdd                        # Show current TDD phase instructions
/sbtdd-init                  # Initialize project scaffolding
/sbtdd-init --ollama         # Initialize with Ollama MAGI backend
/sbtdd-check                 # Verify project setup and state
/sbtdd-override --tool write_file --path src/foo.py  # TDD-Guard override
```

### Tool invocation (LLM-driven)

The LLM can call SBTDD tools programmatically:

- **`sbtdd_status`** — Query current phase, task, and MAGI budget
- **`sbtdd_update_state`** — Mutate state atomically (requires `expected_revision` for OCC)

### TDD-Guard behavior

The `pre_tool_call` hook automatically intercepts writes during TDD phases:

| Phase | Blocked | Allowed |
|-------|---------|---------|
| **Red** | Production code (`write_file`, `patch`) | Test files, reads, tools |
| **Green** | Test modifications | Production code |
| **Refactor** | Nothing (warning: "no new features") | Everything |

Use `/sbtdd-override` to bypass with an audited override budget.

---

## Architecture

```
sbtdd-hermes/
├── plugin.yaml                    # Hermes plugin manifest
├── pyproject.toml                 # Build + entry-point
├── __init__.py                    # Re-export for directory install
├── README.md
├── LICENSE
├── LICENSE-APACHE
├── sbtdd_hermes/
│   ├── __init__.py                  # register(ctx) + hooks + state cache
│   ├── commands.py                  # Slash command handlers
│   ├── state.py                     # SessionState + OCC + filelock + migrate
│   ├── validator.py                 # Field validation + cross-field checks
│   ├── magi_parser.py               # MAGI report parser with timeout
│   ├── _config.py                   # Constants + state machine + regex audit
│   ├── prompts.py                   # Prompt generators
│   ├── scaffolding.py               # Init logic (stack detection, templates)
│   ├── py.typed                     # PEP 561 marker
│   └── scripts/
│       ├── verify.py                # §0.1 verification per stack
│       ├── git_status.py            # Git status + log parser
│       ├── drift_check.py           # Detect state/git drift
│       └── commit_helper.py       # Commit message suggestions
├── templates/
│   ├── HERMES.local.md.tmpl       # ~400 line project rules template
│   ├── spec-behavior-base.tmpl.md # Spec seed
│   └── verification/
│       ├── rust.md                  # Commands §0.1 Rust
│       ├── python.md                # Commands §0.1 Python
│       └── cpp.md                   # Commands §0.1 C/C++
├── references/
│   ├── routing.md                   # Phase detection + artifact map
│   ├── review-gates.md            # Gate criteria + MAGI integration
│   ├── tdd-cycle.md               # TDD procedure + TDD-Guard behavior
│   ├── finalization.md            # Checklist §7
│   └── port-claude-to-hermes.md   # Migration notes + API dependencies
└── tests/
    ├── test_plugin.py               # Registration + hook binding
    ├── test_state.py                # Load/save/OCC/migrate
    ├── test_validator.py            # Cross-field + phase transitions
    ├── test_magi_parser.py          # Parse + timeout + ReDoS
    ├── test_magi_parser_chunks.py   # Streaming chunk robustness
    ├── test_scripts.py              # CLI invocations
    ├── test_config.py               # Constants + state machine
    ├── test_concurrency.py          # OCC concurrent + filelock
    └── test_*.py                    # Commands, status, updates, etc.
```

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Full verification (tests + lint + types)
python -m pytest tests/ -q && ruff check . && mypy sbtdd_hermes/
```

Current status: **115 tests passing, 1 skipped, ruff clean, mypy 0 errors**.

---

## License

Dual-licensed under MIT OR Apache-2.0.

---

## Credits

SBTDD methodology and Hermes plugin by Julian Bolivar.
