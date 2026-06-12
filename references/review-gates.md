# SBTDD Review Gates

## Dual-Loop Pre-Merge Review

### Loop 1 — Automated Review

Run verification commands for your stack. All must pass:
- `python -m sbtdd_hermes.scripts.verify --stack {stack}`

### Loop 2 — MAGI Gate

Invoke `/skill magi` with:
- Full diff (accumulated)
- `sbtdd/spec-behavior.md` as reference
- `planning/hermes-plan-tdd.md` as plan

## MAGI Verdicts

| Verdict | Action |
|---------|--------|
| `STRONG GO` | Merge/PR |
| `GO` | Merge/PR |
| `GO WITH CAVEATS` | Apply conditions, then merge |
| `HOLD -- TIE` | Blocked; fix and re-evaluate |
| `HOLD` | Blocked; fix and re-evaluate |
| `STRONG NO-GO` | Replan from §1 |

## Correction Loop

If MAGI rejects:
1. Read findings
2. Apply fixes as mini-TDD cycles
3. Re-run MAGI
4. Max 3 iterations; escalate if exceeded
