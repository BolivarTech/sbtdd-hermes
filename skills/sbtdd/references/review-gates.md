# sbtdd — Review Gates Reference

This reference covers the two pre-merge review loops, their sequencing,
the MAGI verdict table, and the correction loop with its safety valve.
For commit prefix conventions, see `HERMES.local.md` §5.

---

## 0. Plan Gate (Checkpoint 1 → Checkpoint 2)

This reference also serves the **Plan gate** at planning time.
The plan gate is a strict ordered sequence of two checkpoints.

**Checkpoint 1 — manual review (human gate).** When `planning/hermes-plan-tdd-org.md`
exists and no approved `planning/hermes-plan-tdd.md` exists yet, the orchestrator
**stops** and presents the original plan to the user for explicit approval.

- **Reject:** capture the user's feedback, re-enter the Planning phase, re-run
  `/skill plan` to regenerate `hermes-plan-tdd-org.md` with that feedback
  (regeneration overwrites the prior original plan), then re-present Checkpoint 1.
  Repeat until approved.
- **Approve:** proceed to Checkpoint 2. Never run MAGI before Checkpoint 1
  is approved.

**Checkpoint 2 — MAGI review.** After Checkpoint 1 approval, run `/skill magi`
against `sbtdd/spec-behavior.md` + `planning/hermes-plan-tdd-org.md`, writing
`planning/hermes-plan-tdd.md` from the original plan with the improvements,
iterating until the verdict is `>= GO WITH CAVEATS`. The MAGI verdict table
(§5) and the 3-iteration safety valve (§6) apply identically to this
plan-review loop.

> **Invocation contract:** `/skill magi` is the Hermes skill. It runs on any
> OpenAI-compatible endpoint (Ollama by default). See §7.

---

## 1. Granularity: What Runs When

| Level | When | What runs |
|-------|------|-----------|
| Per TDD-phase close | At the close of each Red / Green / Refactor phase | Verification commands (per stack) + atomic commit + `.hermes/session-state.json` update. No MAGI, no code review. |
| Pre-merge (once) | Once, when the plan's finalization checklist is satisfied | Loop 1: code review then Loop 2: MAGI (both mandatory, in strict sequence) |

`/skill magi` runs **once** over the full accumulated diff, not per task or per
TDD cycle. Running it per cycle introduces overhead without additional signal;
MAGI evaluates architectural trade-offs and design decisions at feature scope.

---

## 2. Sequential Independent Dual Loop

When all finalization preconditions are met, execute two review loops in
strict sequential order:

| Loop | Tool | Exit criterion |
|------|------|----------------|
| **Loop 1** | `/skill requesting-code-review` | Result is *clean to go* — no `[CRITICAL]` or `[WARNING]` findings pending |
| **Loop 2** | `/skill magi` | Verdict ≥ `GO WITH CAVEATS` |

Loop 2 does not start until Loop 1 exits with clean to go.

### Why the loops are kept separate

Each loop detects a different class of defect and their verdicts are not
interchangeable. Running both in parallel (or merging them into a single loop)
produces contaminated verdicts: a mechanical `[WARNING]` from code review
causes MAGI sub-agents (Melchior / Balthasar / Caspar) to emit `CONDITIONAL`
verdicts, degrading consensus to a noisy `GO WITH CAVEATS` or worse, and
hiding design decisions behind mechanical findings.

---

## 3. Step 1 — Code Review (Loop 1)

Automated review against spec, plan, and code standards. The skill produces
prioritized findings (`[CRITICAL]` / `[WARNING]` / `[INFO]`). Procedure:

1. Read all reported findings.
2. Process each finding with technical rigor — understand it before acting;
   reject incorrect suggestions with justification rather than implementing them
   blindly. `[INFO]` findings may be deferred with explicit justification.
3. Apply approved fixes — each fix is its own mini TDD cycle (see
   `HERMES.local.md` §5 for the `test:` → `fix:` → `refactor:` sequence).
4. Each commit in the mini-cycle must pass verification before landing.
5. Repeat code review after each fix batch until the result is **clean to go**
   — zero `[CRITICAL]` and zero `[WARNING]` pending.

`/skill magi` does not run until this condition is met.

---

## 4. Step 2 — MAGI (Final Gate)

Multi-perspective evaluation (Melchior / Balthasar / Caspar) over the already
mechanically-clean diff. **Mandatory**, not optional.

MAGI evaluates what automated review cannot: design trade-offs, architectural
risks, engineering decisions with genuine uncertainty.

> **Invocation contract:** `/skill magi` runs via `execute_code` with direct
> HTTP calls to the configured OpenAI-compatible endpoint. This is the standard
> Hermes skill mechanism — no special restrictions apply.

---

## 5. MAGI Verdict Table

The minimum acceptable verdict to proceed to merge / PR is **`GO WITH CAVEATS`**.

| Verdict | Action |
|---------|--------|
| `STRONG GO` | Proceed to merge / PR without conditions |
| `GO` | Proceed to merge / PR |
| `GO WITH CAVEATS` | Apply the *Conditions for Approval*, then proceed. **No re-evaluation needed** if the conditions are low-risk (documentation, additional tests, naming, logging). **Re-evaluate MAGI** if conditions involve structural changes. |
| `HOLD -- TIE` | **Blocked.** Apply the actions recommended by the individual agents; re-run `/skill magi`. |
| `HOLD` | **Blocked.** Apply the recommended actions; re-run `/skill magi`. |
| `STRONG NO-GO` | **Blocked.** Reconsider the design; this likely requires replanning. |

---

## 6. Correction Loop

When `/skill magi` does not approve (verdict below `GO WITH CAVEATS`):

1. Read the reported findings.
2. Process each finding with technical rigor — defer `[INFO]` with justification.
3. Apply approved fixes using the TDD mini-cycle (`test:` → `fix:` →
   `refactor:`) per `HERMES.local.md` §5.
4. Each commit must pass verification before landing.
5. Re-run `/skill magi` over the accumulated diff.
6. Repeat until verdict ≥ `GO WITH CAVEATS`.

### 3-Iteration Safety Valve

After **3 iterations** of the correction loop without reaching the threshold,
stop and escalate to the user. Possible causes:

- **The plan had a structural defect** — requires replanning (return to
  Specification phase, regenerating the plan with the revised spec).
- **The implementation diverged from the plan** — review alignment between the
  accumulated diff and `planning/hermes-plan-tdd.md`.
- **MAGI detects concerns intrinsic to the approach** that are not visible in
  the plan — requires redefining `sbtdd/spec-behavior.md` and regenerating the
  plan.

---

## 7. MAGI Invocation Contract

`/skill magi` is a standard Hermes skill that runs via `execute_code` with direct
HTTP calls to an OpenAI-compatible endpoint (Ollama by default).

No special invocation restrictions apply beyond those inherent to the
Hermes skill system. The skill may be invoked interactively or via
`execute_code` in scripts.

---

## 8. MAGI Backend Selection

`/skill magi` runs on one of two backends: the default **Ollama** backend
(using local models), or a **custom endpoint**. This section is the single
normative source for backend selection.

> **Verifier:** `/sbtdd-check` Check 8 reports the active backend and, when
> Ollama is configured, smoke-tests it end-to-end. See `commands/sbtdd-check.md`.

### Resolution rule (toml-existence)

On every MAGI invocation the orchestrator makes — Plan-gate Checkpoint 2 (§0)
and Pre-merge Loop 2 (§4) — resolve the backend by the presence of
`./.hermes/magi-ollama.toml`:

| `./.hermes/magi-ollama.toml` | Backend | Invocation |
|------------------------------|---------|------------|
| exists | Ollama (custom models) | `/skill magi` with models from toml |
| absent | Default (Ollama with built-in defaults) | `/skill magi` with built-in defaults |

The file's existence is the persistent signal — it spans the whole
multi-invocation flow.

### Enabling the Ollama backend with custom models

Run `/sbtdd-init --ollama-init`, which scaffolds `./.hermes/magi-ollama.toml`
(idempotent). `.hermes/` is gitignored, so the toml (and any API key) is never
tracked.

### `/sbtdd --ollama` is fail-closed

`/sbtdd --ollama` explicitly requests custom Ollama models. If
`./.hermes/magi-ollama.toml` does **not** exist, the orchestrator **MUST** stop
and instruct the user to run `/sbtdd-init --ollama-init` first. It **MUST NOT**
silently fall back to built-in defaults.

### Dependency: MAGI skill installed

The MAGI skill must be installed in Hermes. If not installed, the orchestrator
reports MAGI as unavailable and skips MAGI-dependent gates.

### Backend unavailable, and switching back

If `./.hermes/magi-ollama.toml` exists but the configured backend is
**unavailable** when MAGI runs — the daemon is unreachable, auth failed, or
the configured trio is missing — MAGI's preflight fails. The orchestrator
**MUST** stop and tell the user to verify the endpoint. It **MUST NOT** silently
fall back.

To switch back to built-in defaults, **remove** `./.hermes/magi-ollama.toml`;
its absence resolves to built-in defaults per the table above.
