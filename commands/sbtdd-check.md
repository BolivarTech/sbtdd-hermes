---
description: Read-only SBTDD setup verifier — diagnoses the full configuration and reports pass/fail per item
---

# /sbtdd-check — SBTDD Setup Verifier

**Run all nine checks** below in order. For each check report `PASS`,
`FAIL <reason>`, or `N/A <reason>` (where applicable) with a one-line
remediation hint. Check 6 may legitimately report `N/A` when no session
state file exists yet.

> **Scope:** This verifier checks the SBTDD infrastructure only (presence of
> files, MAGI reachability, state-file sanity). It does **not** run the MAGI
> gate itself nor inspect the contents of spec/plan documents.
> To switch between MAGI backends, use `--ollama` (see `review-gates.md §8`).

---

## Check 1 — `HERMES.local.md` present with rule sections

- Verify that `HERMES.local.md` exists in the project root.
- Open it and confirm it contains at least the headings for the
  mandatory rule sections (TDD cycle, verification, stack).

**FAIL remediation:** run `/sbtdd-init` to generate it from the template.

---

## Check 2 — Phase discipline tools available

> **Note:** Hermes does not have automatic PreToolUse/SessionStart hooks.
> TDD discipline is enforced cooperatively: user declares phases via
> `TDD-Red:`, `TDD-Green:`, `TDD-Refactor:` and the agent refuses violations.
> This check verifies that the project is configured for cooperative enforcement.

Verify that `.hermes/HERMES.local.md` contains the TDD phase rules and
commit-prefix conventions. If the file is absent, the agent has no
authority to enforce discipline.

| HERMES.local.md present | TDD rules documented | Result |
|---------------------------|----------------------|--------|
| Yes                       | Yes                  | **PASS** |
| No                        | —                    | **FAIL** — run `/sbtdd-init` |
| Yes                       | No                   | **FAIL** — HERMES.local.md is incomplete; regenerate |

**FAIL remediation:** run `/sbtdd-init` to generate/regenerate `HERMES.local.md`.

---

## Check 3 — Working directories exist

Verify that both `sbtdd/` and `planning/` exist in the project root.
Also verify `.hermes/` exists.

**FAIL remediation:** run `/sbtdd-init` to create them.

---

## Check 4 — `.gitignore` contains the five local-only entries

Check that `.gitignore` includes all five of:

```
HERMES.local.md
HERMES.md
.hermes/
sbtdd/
planning/
```

Report which specific entries are missing.

**FAIL remediation:** run `/sbtdd-init` to append the missing lines.

---

## Check 5 — MAGI skill available

Verify that the MAGI skill is installed and reachable:

```bash
hermes skills list
```

Check that `magi` appears under `software-development`.

Also check that the Ollama endpoint (if configured) is reachable:
```bash
curl http://localhost:11434/v1/models
```

**FAIL remediation:** install the MAGI skill via `hermes skills install ...`
and/or verify your Ollama daemon is running.

---

## Check 6 — State-file consistency / drift check

If `.hermes/session-state.json` is absent, report `N/A (no session state
yet)` — this is not a failure.

If the file is present, perform a light drift check inline using the
canonical mapping (`current_phase` is set to the phase to work on NEXT
after a phase closes):

| Last phase-closing commit prefix | `current_phase` SHOULD be |
|----------------------------------|---------------------------|
| `test:`                          | `green`                   |
| `feat:` or `fix:`                | `refactor`                |
| `refactor:`                      | `red` or `done`           |
| `chore:` matching `mark task <id> complete` | `red` or `done` |

Steps:
- Read `current_phase` from `.hermes/session-state.json`.
- If `current_phase == "done"`: report `N/A — plan complete; pre-merge review
  commits (test:/fix:/refactor:) are expected and not drift`. Stop here.
- Read the prefix of the last git commit message.
- Classify the (current_phase, last_commit) pair in order:
  1. **Consistent** — `current_phase` matches the phase implied by the last
     phase-closing commit per the table. Report `PASS`.
  2. **Recoverable lag** — `current_phase` matches the phase that was *closed
     by* the last commit. Report `NOTE`. This is NOT a hard failure.
  3. **DRIFT** — neither of the above. Report `FAIL`.
  4. **Unrecognised prefix — escalate** — the last commit prefix is not one
     of `test:` / `feat:` / `fix:` / `refactor:` / `chore:`. Report `NOTE`.
     Never assume a phase.

**FAIL remediation:** review `.hermes/session-state.json` manually or
run `/sbtdd` to let the orchestrator re-evaluate the phase.

---

## Check 7 — Delegated skills available

Verify that the following skills are installed and reachable:

- `magi` (under `software-development`)
- `plan` (under `software-development`)
- `test-driven-development` (under `software-development`)
- `requesting-code-review` (under `software-development`)
- `systematic-debugging` (under `software-development`)
- `simplify-code` (under `software-development`)

**Fail loud** — list every missing skill explicitly.

**FAIL remediation:** install missing skills via `hermes skills install ...`

---

## Check 8 — Active MAGI backend (and Ollama smoke test)

Report which MAGI backend the SBTDD flow will use, and — when the Ollama
backend is selected — verify it actually works end-to-end. The backend is
resolved by the presence of `./.hermes/magi-ollama.toml`; the normative rule
lives in `review-gates.md §8` (MAGI Backend Selection).

| `./.hermes/magi-ollama.toml` | Active backend | Check 8 action |
|------------------------------|----------------|----------------|
| **absent** | **Claude** (default) | Report `PASS` — "Claude backend (default); no Ollama config to verify." No smoke test runs. |
| **present** | **Ollama** | Run the smoke test below. |

### Ollama smoke test (only when the toml exists)

Verify the Ollama backend is operational by running the real MAGI pipeline
once on a throwaway input. Invoke the `magi` skill with a one-line trivial
input — e.g. `/skill magi "Reply OK."` (the mode is a positional argument).

**Classify the result:**
- **MAGI unavailable** (Check 7 failed) → `FAIL`
- **Preflight abort** (daemon unreachable, auth failed, missing models) → `FAIL`
- **MAGI completes and renders VERDICT banner** → `PASS`
- **Incomplete run** (no verdict banner) → `FAIL`

**FAIL remediation:** fix the Ollama backend per MAGI's reported error, then re-run
`/sbtdd-check`. To switch to the default backend, remove `./.hermes/magi-ollama.toml`.

---

## Check 9 — SBTDD backend configuration

Verify that `.hermes/sbtdd.toml` exists and is parseable. This file configures
the OpenAI-compatible backend (Ollama, OpenRouter, etc.) for automated SBTDD
phases such as specification brainstorming and plan generation.

**Check:**
1. `.hermes/sbtdd.toml` exists.
2. It is valid TOML (parse without error).
3. It contains a `base_url` key with a non-empty value.
4. The `[phases]` table has at least one entry.

**FAIL remediation:** run `/sbtdd-init` to scaffold the file from the template, then edit
the values to match your backend (e.g., `base_url = "http://localhost:11434/v1"`).

> **Note:** The actual API key is never stored in this file; it is read from the
> `SBTDD_BACKEND_API_KEY` environment variable at runtime.

---

## Summary output

After all checks, print a summary table:

| # | Check                              | Result |
|---|------------------------------------|--------|
| 1 | `HERMES.local.md` present          | PASS / FAIL |
| 2 | Phase discipline configured        | PASS / FAIL |
| 3 | `sbtdd/` and `planning/` exist     | PASS / FAIL |
| 4 | `.gitignore` entries               | PASS / FAIL |
| 5 | MAGI skill + Ollama reachable      | PASS / FAIL |
| 6 | State-file drift check             | PASS / FAIL / N/A |
| 7 | Required skills available          | PASS / FAIL |
| 8 | Active MAGI backend (default / Ollama + smoke test) | PASS / FAIL |
| 9 | SBTDD backend config (`sbtdd.toml`) | PASS / FAIL |

If **any check fails**, end with:

> One or more checks failed. Run `/sbtdd-init` to repair the setup,
> then re-run `/sbtdd-check`.

If **all pass**, end with:

> All checks passed. Run `/sbtdd` to start or resume the workflow.
