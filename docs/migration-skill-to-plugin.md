# Migration Guide: Claude SBTDD Skill → Hermes SBTDD Plugin

> **Audience:** Developers migrating from the Claude superpowers/SBTDD-Skill workflow to the native Hermes plugin.

---

## Quick-Start Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Install SBTDD-Hermes as directory plugin | 2 min |
| 2 | Enable plugin: `hermes plugins enable sbtdd` | 30 sec |
| 3 | Restart Hermes | 10 sec |
| 4 | Run `/sbtdd-init` in your project | 1 min |
| 5 | Continue your existing workflow — commands are the same | — |

---

## What Changes (and What Doesn't)

### Architecture Changes

| Feature | Claude Skill | Hermes Plugin | Impact |
|---------|-------------|---------------|--------|
| **Registration** | `CLAUDE.md` + `settings.json` in repo | `pyproject.toml` entry-point + `plugin.yaml` | No action needed — automatic |
| **Commands** | Superpowers `/sbtdd` | Slash commands `/sbtdd`, `/sbtdd-init`, `/sbtdd-check`, `/sbtdd-override` | Same syntax |
| **Tools** | None | `sbtdd_status`, `sbtdd_update_state` | New: agent can query/mutate state |
| **Hooks** | `PreToolUse` (external binary) | Native `pre_tool_call`, `on_session_start` | Same behavior, faster |
| **TDD-Guard** | External guard binary | Native hook with override budget | Same enforcement |
| **State file** | `.claude/state.json` | `.hermes/session-state.json` | Auto-migrated on init |
| **MAGI** | `/skill magi` | Same — install MAGI-Hermes plugin | Unchanged |
| **Backend** | Anthropic Claude | Any Hermes provider (Ollama, OpenRouter, etc.) | More flexibility |

### File Structure Changes

**Before (Claude):**
```
project/
├── CLAUDE.md              # Skill rules (tracked in git)
├── .claude/
│   └── state.json         # Claude state
└── .claude/skills/sbtdd/
```

**After (Hermes):**
```
project/
├── HERMES.local.md         # Project rules (gitignored)
├── .hermes/
│   └── session-state.json  # Hermes state (gitignored)
└── planning/
    └── hermes-plan-tdd.md  # Approved TDD plan (gitignored)
```

> **Key difference:** `CLAUDE.md` was tracked; `HERMES.local.md` is gitignored. Hermes reads it but never modifies it.

---

## Step-by-Step Migration

### Step 1 — Remove Claude artifacts

```bash
# Remove old Claude skill files
rm CLAUDE.md                    # or rename to HERMES.local.md
rm -rf .claude/skills/sbtdd/
rm -rf .claude/state.json
```

### Step 2 — Install SBTDD-Hermes

See [README.md](../README.md) for full installation. Summary:

```bash
git clone https://github.com/BolivarTech/sbtdd-hermes.git
cd sbtdd-hermes

# Windows PowerShell
$pluginsDir = "$env:USERPROFILE\AppData\Local\hermes\plugins\sbtdd"
New-Item -ItemType Directory -Force -Path $pluginsDir
Copy-Item -Path "$(Get-Location)\*" -Destination $pluginsDir -Recurse -Force

# Enable
hermes plugins enable sbtdd

# Restart Hermes
exit && hermes
```

### Step 3 — Initialize project

Inside your project directory (where you previously used SBTDD):

```bash
/sbtdd-init
```

This scaffolds:
- `HERMES.local.md` (from template, ~400 lines)
- `.hermes/session-state.json`
- `.gitignore` entries for SBTDD directories
- `sbtdd/` and `planning/` directories

### Step 4 — Migrate existing state (optional)

If you have an existing `.claude/state.json`, manually port relevant fields to `.hermes/session-state.json`:

| Claude field | Hermes field | Notes |
|--------------|------------|-------|
| `currentPhase` | `current_phase` | Values: "red", "green", "refactor", "done" |
| `currentTaskId` | `current_task_id` | Same |
| `planPath` | `plan_path` | Default: `planning/hermes-plan-tdd.md` |
| `magiBackend` | `magi_backend` | Default: "ollama" |
| `overrideCount` | `tdd_guard_override_count` | Same semantics |
| — | `state_revision` | New: OCC revision counter (start at 0) |
| — | `schema_version` | New: migration version (start at 1) |

> **Tip:** If you don't port, `/sbtdd-init` starts fresh with sensible defaults.

### Step 5 — Verify workflow

```bash
/sbtdd-check
```

Expected output (similar to Claude):
```
SBTDD Project Check
===================
| Check | Status |
|-------|--------|
| HERMES.local.md | ✅ Found |
| .hermes/ directory | ✅ Found |
| session-state.json | ✅ Found |
| planning/ directory | ✅ Found |
| sbtdd/ directory | ✅ Found |
```

---

## Behavior Differences

### TDD-Guard

| Aspect | Claude | Hermes |
|--------|--------|--------|
| Enforcement mechanism | External binary intercepting tools | Native `pre_tool_call` hook |
| Override mechanism | `--override-guard` flag | `/sbtdd-override` command |
| Override budget | Fixed per session | Configurable (`MAX_OVERRIDE_PER_SESSION = 3`) |
| Blocked tools | `write_file`, `patch`, `terminal` | `write_file`, `patch` (terminal removed) |

> **Note:** Hermes TDD-Guard no longer intercepts `terminal`. This means `pytest` and `git status` via terminal are always allowed, even in RED phase.

### MAGI Integration

MAGI is now a **separate Hermes plugin**. Install it alongside SBTDD:

```bash
# MAGI-Hermes directory plugin
git clone https://github.com/BolivarTech/MAGI-Hermes.git
cp -r MAGI-Hermes/. ~/.hermes/plugins/magi/
hermes plugins enable magi
```

The Gate §6 workflow remains identical:
1. Loop 1: Automated review (ruff + mypy + tests)
2. Loop 2: MAGI review (`/skill magi`)

### State Machine

The phase transitions are identical:

```
red → green → refactor → red (next task)
  ↓       ↓         ↓
done    done      done
```

But Hermes adds OCC (Optimistic Concurrency Control):
- `sbtdd_update_state` requires `expected_revision`
- Prevents lost updates if multiple agents modify state

---

## Troubleshooting

### "Plugin not found" after installation

**Cause:** Hermes hasn't scanned plugins or plugin isn't enabled.

**Fix:**
```bash
# Outside Hermes
hermes plugins enable sbtdd
hermes config check

# If still missing, force rescan
rm -rf ~/.hermes/plugins_cache  # if exists
hermes
```

### "TDD-Guard blocks everything"

**Cause:** State file shows `current_phase: "red"` but no test file is being written.

**Fix:**
```bash
/sbtdd-check          # Check current phase
/sbtdd-override --tool write_file --path src/my_file.py
```

Or manually edit `.hermes/session-state.json` to `"current_phase": "done"`.

### "State file corrupted"

**Cause:** Manual edits to `.hermes/session-state.json` broke JSON.

**Fix:**
```bash
rm .hermes/session-state.json
/sbtdd-init           # Recreates with defaults
```

### MAGI review not available

**Cause:** MAGI-Hermes plugin not installed or not enabled.

**Fix:**
```bash
# Install MAGI-Hermes (separate plugin)
git clone https://github.com/BolivarTech/MAGI-Hermes.git
cp -r MAGI-Hermes/. ~/.hermes/plugins/magi/
hermes plugins enable magi
exit && hermes
```

---

## Known Limitations (same as Claude)

1. **Single session per directory:** Concurrent Hermes sessions on same project will contend for `session-state.json`
2. **Heuristic TDD-Guard:** ~85% accuracy; monitor false positives
3. **Windows multiprocessing:** `magi_parser.py` uses `spawn`; ensure no import-time side effects
4. **NFS filesystems:** Cache mtime may truncate to seconds; rare edge case

---

## API Reference for Developers

### Hermes Plugin API surface

```python
# Entry point
from sbtdd_hermes import register
register(ctx)  # ctx: Hermes agent context

# State (for scripts)
from sbtdd_hermes.state import SessionState, load_state, save_state

# Validation (for custom tools)
from sbtdd_hermes.validator import validate_full_update, validate_commit_prefix

# Config (for inspection)
from sbtdd_hermes._config import PHASE_TRANSITIONS, TDDGUARD_TOOL_NAMES
```

---

## Resources

- [SBTDD-Hermes README](../README.md) — Full installation and usage
- [HERMES.local.md template](../templates/HERMES.local.md.tmpl) — Project rules (gitignored)
- [references/tdd-cycle.md](../references/tdd-cycle.md) — TDD procedure details
- [references/review-gates.md](../references/review-gates.md) — Gate §6 criteria
- [references/finalization.md](../references/finalization.md) — Checklist §7

---

**Last updated:** 2026-06-12  
**Version:** SBTDD-Hermes v2.0.0
