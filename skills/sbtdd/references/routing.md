# sbtdd — Routing Reference

This reference describes how the orchestrator determines which phase of the
SBTDD workflow to enter at session start, how authority is resolved across
the three state-carrying artifacts, and how drift between them is detected
and recovered.

---

## 1. State-Detection Decision Table

The orchestrator inspects artifacts in the project tree to choose the correct
entry point. Evaluate rows top-to-bottom; take the first matching row.

| Condition | Phase entered | Action |
|-----------|---------------|--------|
| `sbtdd/spec-behavior-base.md` absent, empty, or still contains any `<!-- replace:` marker | — | **Stop and ask the user to fill it in** before proceeding |
| `sbtdd/spec-behavior-base.md` present; `sbtdd/spec-behavior.md` absent | Specification | Invoke brainstorming using `spec-behavior-base.md` as input |
| `sbtdd/spec-behavior.md` present; `planning/hermes-plan-tdd-org.md` absent | Planning | Invoke `/skill plan` to generate `hermes-plan-tdd-org.md` |
| `planning/hermes-plan-tdd-org.md` present; `planning/hermes-plan-tdd.md` absent or not yet approved | Plan gate (Checkpoint 1 → Checkpoint 2) | **Checkpoint 1 (manual review):** stop and ask the user to review `hermes-plan-tdd-org.md`; on reject, re-enter Planning. **Checkpoint 2 (MAGI):** only after Checkpoint 1 is approved, run MAGI review against spec + plan; iterate until `hermes-plan-tdd.md` is approved with verdict ≥ `GO WITH CAVEATS`. See `references/review-gates.md` §0. |
| Approved `planning/hermes-plan-tdd.md` exists; `session-state.json` present with `current_phase` ≠ `"done"` | Execution — resume | Read `session-state.json`; resume from `current_task_id` / `current_phase` |
| Approved `planning/hermes-plan-tdd.md` exists; `session-state.json` absent | Execution — start | Create `session-state.json` from plan (first `[ ]` task, phase `"red"`) |
| All plan tasks `[x]` and `session-state.json` reports `current_phase: "done"` | Pre-merge review | Run Loop 1 (`/skill requesting-code-review`) then Loop 2 (`/skill magi`) |
| Pre-merge review clean (Loop 1 clean-to-go + Loop 2 ≥ GO WITH CAVEATS) | Finalization | Execute finalization checklist — see `references/finalization.md` |

### Canonical artifact names

| Artifact | Canonical path |
|----------|----------------|
| Spec base | `sbtdd/spec-behavior-base.md` |
| Refined spec | `sbtdd/spec-behavior.md` |
| Original plan | `planning/hermes-plan-tdd-org.md` |
| Approved plan | `planning/hermes-plan-tdd.md` |
| Runtime state | `.hermes/session-state.json` |

---

## 2. Authority Order

Three artifacts carry state about the same TDD progression. When they contain
redundant or conflicting information, the following canon order applies:

```
1. Git is canon of the past   — commits are immutable; the timeline is truth
2. State file is canon of the present — the sole source of "now" during execution
3. Plan is canon of the future + documentary record — what remains + what completed
```

This maps directly to `HERMES.local.md` §2.1. Do not duplicate the rule
tables from that section here; refer to it for the authoritative definition.

---

## 3. Drift Detection and Recovery

**Canonical mapping — phase implied by the last phase-closing commit:**

| Last phase-closing commit prefix | `current_phase` SHOULD be |
|----------------------------------|---------------------------|
| `test:`                          | `green`                   |
| `feat:` or `fix:`                | `refactor`                |
| `refactor:`                      | `red` (next task) or `done` (plan complete) |
| `chore:` with message matching `mark task <id> complete` | `red` (next task) or `done` (plan complete) |

A `chore:` commit counts as a task-close signal **only** when its message
matches `mark task <id> complete`. Any other `chore:` commit (maintenance,
housekeeping, etc.) is NOT a task-close signal — treat it as an unrecognised
prefix and escalate.

`current_phase` is set to the phase to work on **next** after a phase closes.

**Classification rules (evaluate in order):**

1. **N/A** — `current_phase == "done"`: the plan is complete; any post-done
   commits (`test:` / `fix:` / `refactor:` from a pre-merge review mini-cycle)
   are expected and correct. This is NOT drift; do not abort.

2. **Consistent** — `current_phase` equals the phase implied by the last
   phase-closing commit per the table above. Normal state; continue.

3. **Recoverable lag** — `current_phase` matches the phase that was *closed
   by* the last commit (i.e. the commit landed but the state update was
   interrupted before `current_phase` was advanced). This is NOT drift; resume
   by completing the state update and advancing `current_phase`, then
   escalate to the user for confirmation.

4. **DRIFT** — none of the above. `current_phase` does not match either the
   implied next phase or the closed phase. **Abort and escalate to the user
   immediately.** Do not attempt silent reconciliation; silent sync hides
   protocol bugs.

5. **Unrecognised or absent prefix — escalate** — the last commit prefix is
   not one of `test:` / `feat:` / `fix:` / `refactor:` / `chore:` (e.g.
   `docs:`, a merge commit, or no commits yet). **Stop and ask the user.**
   Never assume a phase; never crash.

Recovery procedure (manual, not automatic):

1. Regenerate `session-state.json` from two sources of truth:
   - Plan (`planning/hermes-plan-tdd.md`): find the last `[x]` task.
   - Git: inspect the last commit prefix and SHA.
2. Construct the minimal consistent state from those two sources.
3. **Present the reconstructed state to the user and ask for explicit
   confirmation before resuming any TDD phase.**

Recovery is intentionally manual so that state divergence surfaces as a
conversation rather than a silent assumption.

---

## 4. Autonomous vs. Manual Scope

`session-state.json` is used **only** when an approved `planning/hermes-plan-tdd.md`
exists and the session is running autonomously.

Under **manual fallback** (no approved plan, ad-hoc tasks, hotfixes), the
state file is not read or written. The user controls phase transitions
explicitly in each prompt (`TDD-Red:`, `TDD-Green:`, `TDD-Refactor:`).

For the full state-file schema (fields, types, update protocol), see
`HERMES.local.md` §2.2. This reference describes routing logic only; do not
duplicate the schema here.
