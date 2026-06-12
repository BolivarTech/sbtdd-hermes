# SBTDD TDD Cycle Guide

## TDD-Guard Behavior

The TDD-Guard hook (`pre_tool_call`) enforces phase discipline:

| Phase | Allowed | Blocked |
|-------|---------|---------|
| Red | `write_file` to `test_*.py`, `tests/` | Production code writes |
| Green | `write_file` to production files | Test file modifications |
| Refactor | All writes | — |
| Done | All writes | — |

## Atomic Close (3 steps)

After completing a phase:

1. **Verify:** Run `python -m sbtdd_hermes.scripts.verify --stack {stack}`
2. **Commit:** Use `sbtdd_hermes.scripts.commit_helper --phase {phase} --task "..."`
3. **Advance:** Run `/sbtdd` to update state

## Override

If TDD-Guard blocks legitimate work:
- Use `--override-guard` flag (max 3 per session)
- Logged in state file for audit
