# SBTDD-Hermes — Spec + Behavior + TDD Workflow for Hermes Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Hermes](https://img.shields.io/badge/hermes-compatible-green.svg)](https://hermes-agent.nousresearch.com/docs)

A Hermes Agent skill that implements a **structured, multi-gate software development methodology** forcing specification, planning, adversarial review (MAGI), strict TDD, and pre-merge dual-loop verification before any code reaches `main`.

Ported from the Claude superpowers ecosystem (`.local.md`, `settings.json`, hooks, TDD-Guard) to Hermes, which lacks automatic hooks. The Hermes variant relies on **explicit user prompting for TDD phases** and **agent discipline** instead of tool interception.

---

## Why SBTDD?

Single-pass coding produces brittle code. SBTDD forces five gates before a single line of production code is committed:

1. **Specification** — What behavior must exist?
2. **Planning** — How will that behavior be built?
3. **MAGI Review** — Three adversarial agents challenge the plan
4. **TDD Execution** — Red → Green → Refactor, atomically
5. **Pre-Merge Review** — Automated quality gates + second MAGI pass

This is not bureaucracy. Each gate catches a different class of defect:

| Gate | Catches | Cost if skipped |
|------|---------|----------------|
| Specification | Wrong problem solved | Days of wasted implementation |
| Planning | Architectural mismatch | Refactors touching half the codebase |
| MAGI | Hidden trade-offs, edge cases | Production incidents, security holes |
| TDD | Logic errors, regressions | Bug tickets, hotfixes, rollback |
| Pre-Merge | Style violations, commit hygiene | Code review churn, CI failures |

---

## How It Differs from Claude

| Feature | Claude Ecosystem | Hermes Skill |
|---------|-----------------|--------------|
| Hooks (PreToolUse, SessionStart) | Automatic interception | **Explicit user declaration** (`TDD-Red:`, `TDD-Green:`, `TDD-Refactor:`) |
| TDD-Guard | Blocks file writes without tests | **Agent discipline + user prompting** |
| `.claude/CLAUDE.md` | `.claude/CLAUDE.md` | `~/.hermes/HERMES.md` |
| Session state | `.claude/session-state.json` | `./.hermes/session-state.json` |
| MAGI invocation | `/magi:magi --ollama` | `/skill magi` |
| Planning | `/writing-plans` | `/skill plan` |
| Multi-model parallelism | Claude subagents | `execute_code` + direct HTTP to Ollama |

---

## Workflow Overview

```
1. SPECIFICATION
   sbtdd/spec-behavior-base.md  →  brainstorm  →  sbtdd/spec-behavior.md

2. PLANNING
   /skill plan  →  planning/hermes-plan-tdd-org.md

3. CHECKPOINT 1 — manual user approval of plan

4. CHECKPOINT 2 — MAGI gate
   /skill magi (with spec + plan as payload)
   Iterate until verdict ≥ GO WITH CAVEATS
   → planning/hermes-plan-tdd.md (approved)

5. EXECUTION — serial TDD per task
   For each task in approved plan:
     Red → Green → Refactor
     §0.1 verification before every commit
     Atomic commits: test: / feat: or fix: / refactor:
     Update .hermes/session-state.json after each phase

6. PRE-MERGE REVIEW (one time, after all tasks done)
   Loop 1: requesting-code-review → clean-to-go (0 critical, 0 warning)
   Loop 2: /skill magi on full diff → ≥ GO WITH CAVEATS
   Fixes: mini-TDD cycles with test: → fix: → refactor:

7. FINALIZATION CHECKLIST
   All tasks [x], state file done, §0.1 clean, git status clean,
   MAGI gate passed, commits atomic with correct prefixes
```

---

## Prerequisites

- Hermes Agent installed and configured
- `/skill magi` installed and configured with an Ollama endpoint
- Python 3.11+ (for tests)
- Git repository initialized

---

## Installation

### From GitHub

```bash
# Install directly from the raw SKILL.md URL
hermes skills install https://raw.githubusercontent.com/BolivarTech/sbtdd-hermes/main/skills/sbtdd/SKILL.md

# Verify installation
hermes skills list
# Should show 'sbtdd' under software-development
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/BolivarTech/sbtdd-hermes.git
cd sbtdd-hermes

# Link the skill into your Hermes skills directory (Windows)
mklink /D "%LOCALAPPDATA%\\hermes\\skills\\software-development\\sbtdd" "skills\\sbtdd"

# Reload Hermes to pick up the new skill
hermes reload
```

---

## Quick Start

### 1. Initialize a project for SBTDD

Inside your project's root directory:

```bash
/sbtdd-init
```

This scaffolds:
- `HERMES.local.md` — project-specific rules (from template)
- `.hermes/settings.json` — session defaults
- `sbtdd/` and `planning/` — working directories
- `sbtdd/spec-behavior-base.md` — spec template
- `.gitignore` entries for local-only files

### 2. Verify the setup

```bash
/sbtdd-check
```

Runs 8 checks (all read-only):
1. `HERMES.local.md` present
2. Phase discipline configured
3. Working directories exist
4. `.gitignore` entries correct
5. MAGI skill + Ollama reachable
6. State-file drift check
7. Required skills available
8. Active MAGI backend (with Ollama smoke test when configured)

### 3. Start or resume the workflow

```bash
/sbtdd
```

Routes to the correct phase based on project artifacts.

### 4. Declare TDD phases explicitly

```
TDD-Red: write failing test for parser edge cases
TDD-Green: implement minimum parser logic
TDD-Refactor: extract validation into separate function
```

The agent verifies the declared phase against the state file and refuses
violations.

---

## TDD Phases (User-Guided)

Unlike Claude, Hermes has no automatic phase interception. The user drives the
phase with explicit prefixes:

### TDD-Red: Write failing test

```
User: "TDD-Red: write failing test for parser edge cases"
Agent: Writes test in test_parser.py, verifies it fails, commits with prefix test:
```

### TDD-Green: Make tests pass

```
User: "TDD-Green: implement minimum parser logic"
Agent: Writes production code in parser.py, verifies tests pass, commits with prefix feat:
```

### TDD-Refactor: Clean up

```
User: "TDD-Refactor: extract validation, improve naming"
Agent: Refactors parser.py, verifies tests still pass, commits with prefix refactor:
```

### Phase Violations

If the user asks for production code during Red phase, the agent must refuse:

```
User: "Write the parser now" (during Red phase)
Agent: "We are in TDD-Red phase. I can only write tests. Declare TDD-Green: to proceed."
```

---

## Git Commit Prefixes (enforced)

| Phase | Prefix | Example |
|-------|--------|---------|
| Red | `test:` | `test: add parser edge case for empty input` |
| Green | `feat:` or `fix:` | `feat: implement parser minimum viable logic` |
| Refactor | `refactor:` | `refactor: extract validation into separate fn` |
| Close task | `chore:` | `chore: mark task 3 complete` |

Rules: English only, ≤72 chars subject, imperative mood, no AI refs, no
Co-Authored-By. NEVER commit without explicit user request (unless plan-approved
autonomy was granted per `HERMES.local.md` §5).

---

## Verification Commands

Run these before committing any phase (from `HERMES.local.md` §0.1):

**Rust:**
```bash
cargo nextest run
cargo clippy --all-targets -- -D warnings
cargo fmt --check
cargo build --release
cargo doc --no-deps
cargo audit
```

**Python:**
```bash
pytest
ruff check .
ruff format --check .
mypy .
```

**C/C++ (CMake):**
```bash
cmake --build build --target all
ctest --test-dir build
```

---

## Session State Management

Hermes does not automatically track TDD phase. The agent maintains state manually:

```python
import json
from pathlib import Path

STATE_PATH = Path(".hermes/session-state.json")

def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"current_phase": "idle", "task_index": 0, "tasks": []}

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))
```

The agent calls `load_state()` at the start of each turn and `save_state()` after
each phase transition.

---

## MAGI Gate Integration

SBTDD relies on the MAGI skill for adversarial review.

### MAGI Verdicts

| Verdict | Action |
|---------|--------|
| STRONG GO / GO | Proceed to execution |
| GO WITH CAVEATS | Apply Conditions for Approval; low-risk (docs/naming/logging) may proceed; structural changes require re-eval |
| HOLD / HOLD -- TIE | Blocked. Apply recommended actions, re-run MAGI |
| STRONG NO-GO | Back to spec/plan phase |

### Pre-Merge MAGI Pass

After all tasks complete, run MAGI on the full diff before merging.
Minimum acceptable: **GO WITH CAVEATS**.

---

## Project Structure

```
SBTDD-Hermes/
├── commands/
│   ├── sbtdd.md              -- /sbtdd command
│   ├── sbtdd-init.md         -- /sbtdd-init scaffolding command
│   └── sbtdd-check.md        -- /sbtdd-check verifier command
├── skills/
│   └── sbtdd/
│       ├── SKILL.md          -- Orchestrator (workflow, checkpoints)
│       ├── README.md         -- Full skill guide
│       └── references/
│           ├── routing.md    -- Phase detection + artifact map
│           ├── review-gates.md -- Gate criteria + MAGI integration
│           ├── tdd-cycle.md  -- Execution phase TDD procedure
│           ├── finalization.md -- Branch completion + cleanup
│           └── port-claude-to-hermes.md -- Migration notes
├── templates/
│   ├── HERMES.local.md.tmpl  -- Project rules template
│   ├── settings.json.tmpl    -- Session defaults template
│   ├── spec-behavior-base.tmpl.md -- Spec seed template
│   └── verification/
│       ├── rust.md           -- Rust verification commands
│       ├── python.md         -- Python verification commands
│       └── cpp.md            -- C/C++ verification commands
├── tests/
│   ├── conftest.py           -- Shared fixtures
│   └── test_skill.py         -- Presence / lint tests
├── sbtdd/                    -- (created by /sbtdd-init in target projects)
│   └── spec-behavior-base.md
├── planning/                 -- (created by /sbtdd-init in target projects)
├── pyproject.toml            -- Python packaging + tool config
├── README.md                 -- This file
├── LICENSE                   -- MIT
├── LICENSE-APACHE            -- Apache-2.0
└── .gitignore
```

---

## Troubleshooting

### Agent forgot to read HERMES.md

Stop the session. Restart with:
```
Follow SBTDD. Read ~/.hermes/HERMES.md first.
```

### Session state drift

Check `.hermes/session-state.json`:
```bash
cat .hermes/session-state.json
```

If it does not match reality, regenerate from git history + plan file.

### MAGI gate takes too long

Ensure Ollama is running with multiple models pulled:
```bash
ollama list
```

Configure per-mage models for diversity:
```bash
hermes config set magi.models.melchior qwen3.1:latest
hermes config set magi.models.balthasar llama3.2:latest
hermes config set magi.models.caspar mistral:latest
```

---

## Requirements

| Component | Required | Notes |
|-----------|----------|-------|
| Hermes Agent | Yes | For trigger-mode usage |
| MAGI skill | Yes | For adversarial review gates |
| Ollama endpoint | For MAGI | Ollama, vLLM, LM Studio, etc. |
| Python 3.11+ | For tests | `pytest`, `ruff`, `mypy` |

### Dev Dependencies

```bash
pip install pytest ruff mypy
```

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Full verification (tests + lint + types)
make verify

# Individual checks
make test        # pytest
make lint        # ruff check
make typecheck   # mypy
```

---

## License

Dual licensed under [MIT](LICENSE) OR [Apache-2.0](LICENSE-APACHE), at your option.

---

## Credits

SBTDD methodology ported from the Claude superpowers ecosystem by Julian Bolivar.
Hermes adaptation maintains the same five-gate discipline while accounting for
the absence of automatic tool interception hooks.

Original methodology: © Julian Bolivar.
Hermes migration: © Julian Bolivar and contributors.
