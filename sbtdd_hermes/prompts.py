"""
Prompt generators for the agent.
Builds structured prompts/instructions based on current state.
"""

from pathlib import Path

from .state import SessionState


def build_phase_prompt(phase: str, state: SessionState) -> str:
    """Generate instructions for the current TDD phase."""
    prompts = {
        "red": """You are in TDD-RED phase.

RULES:
- ONLY write test code (files matching test_*.py or in tests/)
- DO NOT write production code yet
- Run verification: `python -m sbtdd_hermes.scripts.verify --stack {stack}`
- Commit with: `test: add test for {task}`

Current task: {task}
Next: After tests pass (fail for right reason), run `/sbtdd` to advance to GREEN.
""",
        "green": """You are in TDD-GREEN phase.

RULES:
- Write MINIMAL production code to make tests pass
- DO NOT modify tests
- Run verification: `python -m sbtdd_hermes.scripts.verify --stack {stack}`
- Commit with: `feat: implement {task}` or `fix: resolve {task}`

Current task: {task}
Next: After all tests pass, run `/sbtdd` to advance to REFACTOR.
""",
        "refactor": """You are in TDD-REFACTOR phase.

RULES:
- Improve code quality WITHOUT changing behavior
- All tests must continue to pass
- Run verification: `python -m sbtdd_hermes.scripts.verify --stack {stack}`
- Commit with: `refactor: clean up {task}`

Current task: {task}
Next: After verification passes, run `/sbtdd` to advance to next task or done.
""",
        "done": """All tasks complete.

FINAL CHECKS:
1. Run `/sbtdd-check` to verify state
2. Review checklist in references/finalization.md
3. Proceed to merge/PR when all checks pass
""",
    }
    
    base = prompts.get(phase, prompts["red"])
    return base.format(
        stack=detect_stack(),
        task=state.current_task_title or "unknown",
    )


def build_verification_prompt(stack: str) -> str:
    """Generate commands for verification."""
    return f"""Run verification for {stack} stack:
```bash
python -m sbtdd_hermes.scripts.verify --stack {stack}
```

All checks must pass before committing.
"""


def build_git_status_prompt() -> str:
    """Generate instructions for git status check."""
    return """Check git status:
```bash
python -m sbtdd_hermes.scripts.git_status
```

Requirements before closing phase:
- No uncommitted changes related to current task
- No untracked files that should be committed
"""


def build_commit_suggestion(phase: str, task_id: str, description: str) -> str:
    """Generate a suggested commit message."""
    from sbtdd_hermes.scripts.commit_helper import suggest_commit
    return suggest_commit(phase, f"{task_id}: {description}")


def build_pre_merge_checklist() -> str:
    """Generate pre-merge checklist."""
    return """## Pre-Merge Checklist

### Loop 1 — Automated Review
- [ ] All tests pass
- [ ] Code style checks pass (ruff, clippy, etc.)
- [ ] Type checking passes (mypy)
- [ ] No critical warnings

### Loop 2 — MAGI Gate
- [ ] Run `/skill magi` on full diff
- [ ] Veredicto >= `GO WITH CAVEATS`
- [ ] Apply conditions if any

### Final
- [ ] `git status` clean
- [ ] All tasks marked [x] in plan
- [ ] State file shows `current_phase: done`
"""


def build_magi_payload(spec_path: Path, plan_path: Path) -> str:
    """Generate payload for MAGI review."""
    spec = spec_path.read_text(encoding="utf-8") if spec_path.exists() else "(spec not found)"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else "(plan not found)"
    
    return f"""Please review the following implementation against spec and plan.

## Spec (sbtdd/spec-behavior.md)
{spec[:2000]}

## Plan (planning/hermes-plan-tdd.md)
{plan[:2000]}

Evaluate: completeness, correctness, adherence to spec, potential risks.
"""


def detect_stack() -> str:
    """Detect stack from current directory."""
    from .scaffolding import detect_stack as _detect
    import os
    stack = _detect(Path(os.getcwd()))
    return stack or "python"
