# sbtdd — TDD Cycle Reference

This reference describes the per-phase rules, the non-negotiable atomic close
procedure, bookkeeping at Refactor close, and failure handling. For commit
prefix conventions, see `HERMES.local.md` §5. For verification commands, see
`HERMES.local.md` §0.1. For the state-file schema and update protocol, see
`HERMES.local.md` §2.2.

---

## 1. Per-Phase Rules

| Phase | Allowed | Blocked |
|-------|---------|---------|
| **Red** | Write tests that fail. Minimal stubs to compile (no real logic). | Production code. Tests that pass without an implementation. |
| **Green** | Minimum implementation to make existing tests pass. | Modifying tests. Adding functionality not required by any test. |
| **Refactor** | Improve structure, names, remove duplication, add doc-comments. | Adding functionality. Modifying tests. Changing observable behavior. |

If user-declared phase (`TDD-Red:`, `TDD-Green:`, `TDD-Refactor:`) and
skill guidance disagree, the user's declared phase takes precedence — it is
their instruction.

---

## 2. Bookkeeping Note at Refactor Close

At the close of the Refactor phase, two bookkeeping actions are required:

1. Mark the checkbox `[x]` in `planning/hermes-plan-tdd.md` for the completed
   task.
2. Update `.hermes/session-state.json` per the protocol in `HERMES.local.md` §2.3.

These actions are **not** "adding functionality" and do not violate Refactor's
blocked list. They are administrative task-close bookkeeping.

---

## 3. Atomic 3-Step Close (Non-Negotiable)

Every phase — Red, Green, Refactor — must be closed with the following three
steps in strict order. A phase is not considered approved until all three
complete successfully.

### Step 1 — Verification

Run the verification commands listed in `HERMES.local.md` §0.1 for the project's
stack and present their output as evidence. "It should pass" is not evidence —
the actual command output is.

### Step 2 — Atomic Commit

Only after Step 1 passes cleanly, create an atomic commit using the prefix
corresponding to the phase (see `HERMES.local.md` §5). The commit must contain
**only** the diff of that phase. Do not mix Red with Green, Green with Refactor,
or different tasks in a single commit.

### Step 3 — Update `session-state.json`

After the commit, update `session-state.json` to reflect the transition:
advance `current_phase`, record `phase_started_at_commit` (the SHA of the
commit just created), and update `last_verification_at` and
`last_verification_result`. Full protocol in `HERMES.local.md` §2.3.

#### Refactor-close fork

When the closed phase is Refactor, the task is complete. Two sub-cases apply:

- **Next `[ ]` task exists in plan** — commit the checkbox update with
  `chore: mark task {id} complete`; advance `current_task_id` /
  `current_task_title` to that task and reset `current_phase` to `"red"`.
- **No next `[ ]` task (last task)** — commit the checkbox update with
  `chore: mark task {id} complete`; set `current_task_id: null`,
  `current_task_title: null`, `current_phase: "done"` in `session-state.json`.
  This enables the finalization flow (see `references/finalization.md`).

---

## 4. Cooperative Enforcement Under Hermes

Hermes does not have automatic PreToolUse hooks. TDD discipline is enforced
cooperatively:

### Default Mode: Serial Execution

One task at a time, each running its own Red→Green→Refactor cycle.
This is the default and preferred mode.

Suggest parallel execution only when **both** conditions hold:
1. There is a **perceptible time gain** from running tasks concurrently.
2. The tasks are **mutually independent** — no shared state and no cross-task
   dependencies.

When in doubt, stay serial.

### Phase Transition Flow

```
User: "TDD-Red: write failing test for parser edge cases"
  → Agent verifies phase is "red" (or expected next phase)
  → Agent writes test, verifies it fails
  → Agent runs verification commands
  → Agent commits with prefix "test:"
  → Agent updates session-state.json: current_phase = "green"

User: "TDD-Green: implement minimum parser logic"
  → Agent verifies phase is "green"
  → Agent writes production code, verifies tests pass
  → Agent runs verification commands
  → Agent commits with prefix "feat:"
  → Agent updates session-state.json: current_phase = "refactor"

User: "TDD-Refactor: clean up"
  → Agent verifies phase is "refactor"
  → Agent refactors, verifies tests still pass
  → Agent runs verification commands
  → Agent commits with prefix "refactor:"
  → Agent marks task checkbox, commits with "chore:"
  → Agent updates session-state.json for next task or "done"
```

If the user declares a wrong phase (e.g., "TDD-Green:" when state says "red"):
- The agent must refuse, explain the expected phase, and ask the user to confirm.
- Exception: if the user explicitly overrides with "FORCE TDD-Green:", the agent
  may proceed after logging the override in the conversation.

---

## 5. Spec Precedence on Ambiguity

When `sbtdd/spec-behavior.md` and `planning/hermes-plan-tdd.md` contradict each
other, **`spec-behavior.md` wins** — it is the authoritative behavioral contract.
Consult `sbtdd/spec-behavior.md` before assuming any behavior; do not implement
behavior that is absent from the spec.

---

## 6. On Unexpected Test Failure

If a test fails unexpectedly during any phase, invoke `/skill systematic-debugging`
before proposing a fix. Diagnose the root cause; do not patch the symptom. Only
after the diagnosis is clear should a fix be applied, verified, and committed.
