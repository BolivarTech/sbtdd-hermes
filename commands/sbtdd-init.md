---
description: Scaffold a project for the SBTDD workflow — multi-stack, idempotent setup
---

# /sbtdd-init — SBTDD Project Scaffolding

This command initialises a project for the SBTDD workflow. It is **idempotent:
do not overwrite** files that already exist; always report what was
created and what was skipped.

---

## Step 1 — Detect the build stack

Scan the project root for these manifest files:

| File            | Stack  |
|-----------------|--------|
| `Cargo.toml`    | rust   |
| `pyproject.toml` or `setup.py` | python |
| `CMakeLists.txt` | cpp    |

- If exactly one match: proceed with that stack.
- If more than one match or none: **pause and ask the user** which stack
  to configure (AskUserQuestion). Do not guess.

---

## Step 2 — Write `HERMES.local.md`

Source template: `${PLUGIN_ROOT}/templates/HERMES.local.md.tmpl`

Substitutions:
- `{StackVerification}` → contents of
  `${PLUGIN_ROOT}/templates/verification/<stack>.md`
  (where `<stack>` is `rust`, `python`, or `cpp`)
- §4 stack line → replace the literal `(filled by /sbtdd-init)` on the §4 Stack line with the detected stack (language, test runner, test command).
- `{ErrorType}` → ask the user for their preferred error/exception type
  (or leave `TODO: set ErrorType` if the user skips)
- `{Author}` → ask the user for their name/handle
  (or leave `TODO: set Author` if the user skips)

If `HERMES.local.md` already exists: **skip it and report "skipped (already
present)"**. Do not overwrite.

---

## Step 3 — Write / merge `.hermes/settings.json`

> **Note:** Hermes does not have automatic hooks (PreToolUse, SessionStart).
> The settings.json file stores session defaults and tool preferences, but
> TDD enforcement relies on agent discipline and user-declared phase prefixes
> (`TDD-Red:`, `TDD-Green:`, `TDD-Refactor:`), not automatic interception.
> See `references/port-claude-to-hermes.md` for details.

If `.hermes/settings.json` does not exist:
Copy the template verbatim. Create `.hermes/` first if absent.

If `.hermes/settings.json` already exists (merge strategy):
1. **Back it up** with a non-clobbering filename:
   - Attempt `.hermes/settings.json.bak`.
   - If that file already exists, use a timestamped name instead.
   - Never overwrite an existing backup.
2. Parse both files as JSON.
3. Merge only new keys from the template; never modify existing keys.
4. Show the unified diff and backup path before writing.
5. Validate after writing by re-reading and parsing the JSON.
6. If parsing fails, restore from backup and report error.

---

## Step 4 — Create working directories

```
sbtdd/
planning/
.hermes/
```

Create all if absent. If already present, skip silently.

---

## Step 5 — Seed `sbtdd/spec-behavior-base.md`

Source template: `${PLUGIN_ROOT}/templates/spec-behavior-base.tmpl.md`

Copy to `sbtdd/spec-behavior-base.md` **only if the file does not already
exist**. If it exists, skip and note it in the report.

---

## Step 6 — Update `.gitignore`

Append entries that are not already present in `.gitignore`
(create `.gitignore` if absent).

The checked set consists of these five content entries:

```
HERMES.local.md
HERMES.md
.hermes/
sbtdd/
planning/
```

**Already-tracked warning:** before appending any entry, run
`git ls-files -- <path>` for each of the five entries in the target repo.
If any path is **already tracked** by git, emit a **PROMINENT WARNING** and
ask the user whether to proceed, skip those entries, or abort.

**Exact-line matching:** when checking whether an entry already exists, match
the **full line exactly** (strip leading/trailing whitespace; also treat a
line with an optional trailing `/` as matching the bare form).

The comment line `# SBTDD local-only files` is added once only if it is
not already present.

> **If invoked as `/sbtdd-init --ollama-init`:** before the final report, also
> perform the **Optional flag: `--ollama-init`** section below (Ollama MAGI
> backend setup).

---

## Optional flag: `--ollama-init`

When `/sbtdd-init` is invoked as `/sbtdd-init --ollama-init`, then after the
steps above, delegate to MAGI's `--ollama-init` to scaffold
`./.hermes/magi-ollama.toml`. Its presence selects the Ollama backend
for every MAGI invocation in the SBTDD flow — see `review-gates.md §8` (MAGI
Backend Selection).

- **Idempotent:** if `./.hermes/magi-ollama.toml` already exists, skip it and
  report "skipped (already present)"; never overwrite.
- `.hermes/` is gitignored (Step 6), so the toml (and any API key) is not tracked.
- Requires **MAGI skill installed**; if MAGI is not installed, report that
  the Ollama backend is unavailable and skip this step.
- Without `--ollama-init`, `/sbtdd-init` does NOT create the toml and the flow
  uses the default MAGI backend.

---

## Step 7 — Final report

Print a summary table:

| Item                          | Status          |
|-------------------------------|-----------------|
| `HERMES.local.md`             | created / skipped |
| `.hermes/settings.json`       | created / merged / skipped |
| `.hermes/settings.json.bak`   | created / n/a   |
| `sbtdd/`                      | created / skipped |
| `planning/`                   | created / skipped |
| `.hermes/`                    | created / skipped |
| `sbtdd/spec-behavior-base.md` | created / skipped |
| `.hermes/magi-ollama.toml` (with `--ollama-init`) | created / skipped / n/a |
| `.gitignore` entries          | added N / all present |

Then remind the user:

> **Next steps**
> 1. Run `/sbtdd-check` to verify the full setup.
> 2. Start a feature with `TDD-Red:` to enter the SBTDD workflow.
