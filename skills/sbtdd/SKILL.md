---
name: sbtdd
description: >
  Drive or resume the SBTDD (Spec + Behavior + Test-Driven Development)
  multi-agent workflow for Hermes Agent. Use when running /sbtdd, starting an
  SBTDD feature, continuing an in-progress TDD plan, or when the user mentions
  SBTDD, spec-behavior, or the hermes-plan-tdd flow. Inspects project artifacts
  and .hermes/session-state.json, then executes the next phase.
version: 1.0.0
author: Julian Bolivar
license: MIT OR Apache-2.0
metadata:
  hermes:
    tags: [sbtdd, tdd, spec-driven, workflow, magi, multi-agent, ollama]
    related_skills: [magi, test-driven-development, plan, systematic-debugging, requesting-code-review]
---

# SBTDD Orchestrator Skill

This skill drives the full SBTDD lifecycle. It routes to the correct phase,
delegates to the appropriate skills, and enforces human gates.
Per-phase detail lives in the `references/` directory; this file holds only
the routing skeleton and the delegation table.

## 5-Step Operating Procedure

### 1. Preflight

Verify that `HERMES.local.md`, `sbtdd/`, and `planning/` exist in the project
root. If any are missing, **stop immediately** and tell the user:

> "Required SBTDD artifacts are missing. Run `/sbtdd-init` to initialize the
> project. For a full integrity check, run `/sbtdd-check`."

Do not proceed past Preflight until the project is initialized.

Also verify that the global rules are loaded:
1. `~/.hermes/HERMES.md` — user's global coding standards (precedence absolute).
2. `./.hermes/HERMES.local.md` — project-specific rules.
   Fallback if not in repo: `~/.hermes/HERMES.local.md`.

Conflict → global wins. Deviation → escalate to user.

### 2. Route

Read `references/routing.md`. Detect the current phase by inspecting the
artifacts that are actually present on disk (use terminal/file tools — file
existence is the deterministic ground truth). On state drift or ambiguity,
abort and escalate to the user. **Announce the detected phase and the evidence
found**, and confirm with the user before acting when the phase is ambiguous.

### 3. Execute

Read the reference file for the detected phase (see delegation table below)
and invoke the listed skill(s) using their Hermes skill names.

| Detected phase | Reference to read | Hermes skill(s) |
|---|---|---|
| Spec refinement | routing.md | `plan` (brainstorming mode) |
| Planning | routing.md | `plan` |
| Plan gate | review-gates.md | manual review (Checkpoint 1) → `magi` (Checkpoint 2) |
| Execution | tdd-cycle.md | `test-driven-development`, `requesting-code-review`, `systematic-debugging`; optional `simplify-code` |
| Pre-merge review | review-gates.md | `requesting-code-review` → `magi` |
| Finalization | finalization.md | branch completion |

> **Execution default:** serial execution is the preferred mode. The user
> drives phase transitions explicitly via `TDD-Red:`, `TDD-Green:`,
> `TDD-Refactor:`. See `references/tdd-cycle.md` §4.

> **MAGI backend:** the orchestrator resolves the MAGI backend per
> `review-gates.md §8` — if `./.hermes/magi-ollama.toml` exists, every `magi`> invocation (Plan gate, Pre-merge review) uses custom models from that toml;> `/sbtdd --ollama` is the explicit fail-closed form. Enable it with
> `/sbtdd-init --ollama-init`.

### 4. Gates

Human stops are mandatory and ordered at the plan gate: **Checkpoint 1** (manual
review of `hermes-plan-tdd-org.md`) precedes **Checkpoint 2** (the `magi`
verdict); never run MAGI before Checkpoint 1 is approved. Never auto-approve any
gate. Wait for explicit human confirmation before advancing to the next phase.

### 5. Loop

After a phase closes, re-route (return to step 2). Under an approved plan, the
orchestrator may continue autonomously according to the rules in
`HERMES.local.md` §5 without prompting between sub-steps.

## Authority Chain (read before any code)

At the start of every development session, read and enforce in this order:

1. `~/.hermes/HERMES.md` — user's global coding standards (precedence absolute).
2. `./.hermes/HERMES.local.md` — project-specific rules and SBTDD flow.
   Fallback if not in repo: `~/.hermes/HERMES.local.md`.

Conflict → global wins. Deviation → escalate to user.

## Hermes-Specific Adaptations (vs Claude)

| Claude Feature | Hermes Equivalent |
|---|---|
| `.claude/CLAUDE.md` | `~/.hermes/HERMES.md` |
| `.claude/settings.json` hooks (PreToolUse, SessionStart, UserPromptSubmit) | **None**. TDD enforcement via explicit user declaration: `TDD-Red:`, `TDD-Green:`, `TDD-Refactor:` |
| TDD-Guard (automatic file-write blocking) | **None**. Agent discipline + user prompting |
| `.claude/session-state.json` | `./.hermes/session-state.json` (gitignored, manual read/write) |
| `/magi:magi --ollama` | `/skill magi` (orchestrator auto-detects Ollama) |
| `/subagent-driven-development` (parallel agents with different models) | `execute_code` + direct HTTP to Ollama for model diversity. `delegate_task` gives same model to all children |
| `/writing-plans` | `/skill plan` |

## Workflow Overview

```
1. SPECIFICATION
   sbtdd/spec-behavior-base.md  →  prompt/manual brainstorm  →  sbtdd/spec-behavior.md

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
   Loop 1: automated review → clean-to-go (0 critical, 0 warning)
   Loop 2: /skill magi on full diff → ≥ GO WITH CAVEATS
   Fixes: mini-TDD cycles with test: → fix: → refactor:

7. FINALIZATION CHECKLIST
   All tasks [x], state file done, §0.1 clean, git status clean,
   MAGI gate passed, commits atomic with correct prefixes
```

## §0.1 Verification Commands

Run these before committing any phase (per stack, from `HERMES.local.md`):

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

## MAGI Gate Verdicts

| Verdict | Action |
|---------|--------|
| STRONG GO / GO | Proceed to execution |
| GO WITH CAVEATS | Apply Conditions for Approval; low-risk (docs/naming/logging) may proceed; structural changes require re-eval |
| HOLD / HOLD -- TIE | Blocked. Apply recommended actions, re-run MAGI |
| STRONG NO-GO | Back to spec/plan phase |

## Parallelism Rules (Hermes limitation)

- **Default**: serial execution, one task at a time.
- **Parallel**: only via `delegate_task` (max 3 concurrent, **same model**).
- **Model diversity**: for MAGI or other multi-model needs, use `execute_code`
  with direct HTTP calls to Ollama, passing distinct `model` per request.

## Recovery

If `.hermes/session-state.json` is lost or corrupted:
1. Regenerate from git (last commit) + plan (last [x]).
2. Escalate to user for confirmation before continuing.
3. Never auto-sync state file with git silently — drift hides protocol bugs.

## References

- User's global rules: `~/.hermes/HERMES.md`
- Project rules (repo-local): `./.hermes/HERMES.local.md`
- Fallback project rules: `~/.hermes/HERMES.local.md`
- MAGI orchestrator: see skill `magi` and its `scripts/hermes_magi.py`
- Routing: `skills/sbtdd/references/routing.md`
- Review gates: `skills/sbtdd/references/review-gates.md`
- TDD cycle: `skills/sbtdd/references/tdd-cycle.md`
- Finalization: `skills/sbtdd/references/finalization.md`
- Porting notes: `skills/sbtdd/references/port-claude-to-hermes.md`

## Pitfalls

1. **Forgetting to read HERMES files first**. Always read them before accepting
   a coding task. They override any default behavior.
2. **Assuming Claude hooks exist**. Hermes has no PreToolUse/SessionStart hooks.
   TDD enforcement is cooperative, not automatic.
3. **Using `delegate_task` for MAGI diversity**. All subagents inherit the same
   model. Use `execute_code` + HTTP for true multi-model parallelism.
4. **Skipping Checkpoint 2 (MAGI gate)**. Do not start execution until the plan
   has passed MAGI with ≥ GO WITH CAVEATS.
5. **Mixing phases in one commit**. Red, Green, and Refactor must each be their
   own atomic commit.

## File Layout

```
sbtdd/
  SKILL.md                         -- This file (orchestrator, workflow)
  README.md                        -- Full installation and usage guide
  references/
    routing.md                     -- Phase detection rules and artifact map
    review-gates.md                -- Gate criteria and MAGI integration
    tdd-cycle.md                   -- Execution phase TDD procedure
    finalization.md                -- Branch completion and cleanup
    port-claude-to-hermes.md       -- Migration notes (Claude → Hermes)
```

## Verification Checklist

- [ ] `hermes skills list` shows `sbtdd` under `software-development`
- [ ] `~/.hermes/HERMES.md` exists and is readable
- [ ] Repo has `planning/` directory or user approves creation
- [ ] `/skill magi` installed and Ollama endpoint reachable
- [ ] Test invocation: user triggers SBTDD, agent reads HERMES files before any code
