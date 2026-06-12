# SBTDD Routing Guide

## Phase Detection

The SBTDD plugin detects the current phase by reading `.hermes/session-state.json`:

| `current_phase` | Meaning |
|----------------|---------|
| `"red"` | Write tests only |
| `"green"` | Write production code |
| `"refactor"` | Clean up code |
| `"done"` | All tasks complete |

## Artifact Map

| Artifact | Path | Tracked by git? |
|----------|------|-----------------|
| HERMES.local.md | `./HERMES.local.md` | No |
| Session state | `.hermes/session-state.json` | No |
| Spec base | `sbtdd/spec-behavior-base.md` | No |
| Spec | `sbtdd/spec-behavior.md` | No |
| Plan | `planning/hermes-plan-tdd.md` | No |

## Drift Recovery

If state and git history disagree:

1. Run `python -m sbtdd_hermes.scripts.drift_check`
2. If DRIFT: reload from git (last commit) + plan (last `[x]` task)
3. If RECOVERABLE_LAG: continue from current state
4. If UNRECOGNISED: escalate to user
