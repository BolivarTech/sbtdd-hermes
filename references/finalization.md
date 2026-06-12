# SBTDD Finalization Checklist

## §7 — Completion Criteria

- [ ] All tasks marked `[x]` in `planning/hermes-plan-tdd.md`
- [ ] `.hermes/session-state.json` shows `current_phase: "done"`
- [ ] All verification commands pass
- [ ] `git status` clean (no uncommitted changes)
- [ ] Spec and plan reflect final state
- [ ] MAGI gate approved (verdict >= `GO WITH CAVEATS`)
- [ ] Autonomous loop completed (if applicable)
- [ ] Commits follow §5 conventions

## Git Status Check

```bash
python -m sbtdd_hermes.scripts.git_status
```

Requirements:
- No modified files related to plan tasks
- No untracked files that should be committed
- Only allowed untracked: documented in `.gitignore`
