# SBTDD-Hermes — Spec + Behavior + TDD Plugin for Hermes Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Hermes](https://img.shields.io/badge/hermes-compatible-green.svg)](https://hermes-agent.nousresearch.com/docs)

**Version: 2.0.0**

A native Hermes Agent plugin implementing structured SBTDD (Spec + Behavior + TDD) methodology with automatic TDD-Guard enforcement, MAGI integration, and pre-merge dual-loop verification.

Ported from the Claude superpowers ecosystem to Hermes native plugin architecture with `pre_tool_call` hooks, slash commands, and agent tools.

---

## Why SBTDD?

Single-pass coding produces brittle code. SBTDD forces five gates before a single line of production code is committed:

1. **Specification** — What behavior must exist?
2. **Planning** — How will that behavior be built?
3. **MAGI Review** — Three adversarial agents challenge the plan
4. **TDD Execution** — Red → Green → Refactor with tool interception
5. **Pre-Merge Verification** — Automated + MAGI dual-loop review

---

## Installation

```bash
git clone https://github.com/BolivarTech/sbtdd-hermes.git
cd sbtdd-hermes
pip install -e .
```

### Enable in Hermes

```bash
hermes config set plugins.enabled "[sbtdd]"
# Restart Hermes
```

The plugin registers automatically via the `hermes_agent.plugins` entry-point declared in `pyproject.toml`.

---

## Commands

| Command | Purpose |
|---------|---------|
| `/sbtdd` | Show current TDD phase instructions |
| `/sbtdd-init` | Initialize project scaffolding |
| `/sbtdd-init --ollama` | Initialize with Ollama backend |
| `/sbtdd-check` | Verify project setup and state |
| `/sbtdd-override --tool write_file --path src/foo.py` | Set TDD-Guard override |

---

## Tools

| Tool | Schema | Purpose |
|------|--------|---------|
| `sbtdd_status` | `{phase, task_id, task_title, magi_iterations, magi_backend}` | Query current state |
| `sbtdd_update_state` | `{field, value, expected_revision}` | Agent-writable state mutation |

---

## Hooks

| Hook | Purpose |
|------|---------|
| `pre_tool_call` | TDD-Guard: blocks writes violating phase rules |
| `on_session_start` | Resume session from saved state |

---

## Architecture

```
sbtdd-hermes/
├── pyproject.toml                    # Entry-point: hermes_agent.plugins
├── sbtdd_hermes/
│   ├── __init__.py                   # register(ctx) + hooks + state cache
│   ├── commands.py                   # Slash command handlers
│   ├── state.py                      # SessionState + OCC + filelock + migrate
│   ├── validator.py                  # Field validation + cross-field checks
│   ├── magi_parser.py                # MAGI report parser with timeout
│   ├── _config.py                    # Constants + state machine
│   ├── prompts.py                    # Prompt generators
│   ├── scaffolding.py                # Init logic
│   └── scripts/                      # Verification runners
├── templates/                        # HERMES.local.md, verification per stack
└── references/                       # Guides for LLM
```

---

## Requirements

| Component | Required | Notes |
|-----------|----------|-------|
| Hermes Agent | Yes | Native plugin support |
| MAGI skill | Optional | For adversarial review gates |
| Python 3.11+ | Yes | `pytest`, `ruff`, `mypy`, `filelock` |

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Full verification (tests + lint + types)
python -m pytest tests/ -v && ruff check . && mypy .
```

---

## License

Dual licensed under [MIT](LICENSE) OR [Apache-2.0](LICENSE-APACHE), at your option.

---

## Credits

SBTDD methodology and Hermes plugin by Julian Bolivar.
