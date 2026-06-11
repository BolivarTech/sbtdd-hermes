# sbtdd — Finalization Reference

This reference covers the git-status verification, the final checklist, pending-change
resolution, and the handoff to branch completion.
For commit prefix conventions, see `HERMES.local.md` §5. For verification
commands, see `HERMES.local.md` §0.1.

---

## 1. Clean Git-Status Verification

Before invoking branch completion, the working tree must be clean with respect
to the plan's scope.

```bash
git status     # No modified, staged, or untracked files within plan scope
```

### Approval Criteria

- **No modified or staged files** related to any plan task. Every in-scope
  change must already be in an atomic commit.
- **No untracked files** that should be part of the plan. New files required
  by the plan must be committed. New files outside the plan must be in
  `.gitignore` or removed.
- **Permitted untracked files** are only those the project already documents
  as intentionally ignorable.

If `git status` shows pending changes within plan scope, the plan is **not**
complete — see Section 3 below.

---

## 2. Final Checklist

All items must be verified by the agent before branch completion.

- [ ] All plan tasks marked `[x]` in `planning/hermes-plan-tdd.md`
- [ ] `.hermes/session-state.json` reports `current_task_id: null`,
  `current_task_title: null`, and `current_phase: "done"`
- [ ] All verification commands in `HERMES.local.md` §0.1 pass without warnings
- [ ] `git status` clean with respect to plan scope (Section 1 criteria above)
- [ ] `sbtdd/spec-behavior.md` and `planning/hermes-plan-tdd.md` reflect the final state
- [ ] Code review executed and all findings resolved (Loop 1 clean to go)
- [ ] **MAGI gate approved** — `/skill magi` verdict ≥ `GO WITH CAVEATS`; if the
  verdict was `GO WITH CAVEATS`, all structural *Conditions for Approval* applied
  before merge (see `references/review-gates.md` §5)
- [ ] Commits follow the prefix conventions in `HERMES.local.md` §5 (atomic,
  correct prefix per context)
- [ ] `HERMES.md` updated if any durable architectural decisions were made

Only when every checklist item is checked, proceed to branch completion.

---

## 3. Pending-Change Resolution

If `git status` reports changes related to plan scope, resolve before closing:

1. Identify which plan task the pending change belongs to.
2. Return to that task's TDD cycle: verify the phase, run verification commands,
   commit atomically with the correct prefix.
3. If the change does not correspond to any plan task, it is **scope creep**:
   revert it or move it to a separate plan. Do not commit it under the current
   plan.

No pending changes may be bundled into a catch-all commit to clear the status.
Each commit must be atomic and belong to a specific TDD phase or task close.
