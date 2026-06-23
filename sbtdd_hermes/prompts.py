"""
Prompt generators for the agent.
Builds structured prompts/instructions based on current state.
"""

import re
from pathlib import Path

from .state import SessionState

# Maximum spec-base size to avoid context-window exhaustion
_MAX_SPEC_BYTES = 100_000
# Minimum fence length for the markdown code block
_MIN_FENCE_LEN = 4


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


def _max_consecutive_backticks(text: str) -> int:
    """Return the maximum number of consecutive backticks in text."""
    max_count = current = 0
    for ch in text:
        if ch == "`":
            current += 1
            max_count = max(max_count, current)
        else:
            current = 0
    return max_count


def _is_fence_safe(content: str, fence: str) -> bool:
    """Check that no line in content can close the given fence.

    CommonMark allows a closing fence to be preceded by up to 3 spaces
    and followed by arbitrary spaces/tabs. The closing fence must have
    AT LEAST as many backticks as the opening fence. We scan every line
    for any line that matches: 0-3 spaces + fence + zero or more extra
    backticks + only spaces/tabs.
    """
    # Note: f-string + re.escape means we write "{{0,3}}" to produce
    # regex "{0,3}" for the space quantifier, while fence is safely escaped.
    pattern = re.compile(rf"^ {{0,3}}{re.escape(fence)}`*[ \t]*$")
    for line in content.splitlines():
        if pattern.match(line):
            return False
    return True


def _compute_fence(content: str) -> tuple[str, str]:
    """Return (open_fence, close_fence) that cannot be broken by content.

    Strategy:
    1. Start with fence_len = max(4, max_consecutive_backticks + 1).
    2. If any line in content could close this fence (per CommonMark),
       increment fence_len and re-check until safe.
    3. Fence length is unbounded; backticks are cheap in context-window terms.
    """
    needed = _max_consecutive_backticks(content) + 1
    fence_len = max(_MIN_FENCE_LEN, needed)

    # Ensure no line in content can close the fence
    while True:
        fence = "`" * fence_len
        if _is_fence_safe(content, fence):
            return f"{fence}markdown", fence
        fence_len += 1


def build_brainstorm_prompt(root: Path) -> str:
    """Generate an active brainstorm prompt from spec-behavior-base.md.

    Reads the spec base, truncates if it exceeds _MAX_SPEC_BYTES, detects
    the longest run of backticks in the content, and wraps it in a markdown
    fenced code block whose fence cannot be prematurely closed by any line
    in the content (per CommonMark spec §4.5).
    Returns a full prompt instructing the agent to write sbtdd/spec-behavior.md.
    """
    spec_base = root / "sbtdd" / "spec-behavior-base.md"

    if not spec_base.exists():
        return (
            "# SBTDD Workflow\n\n"
            "**Phase: Specification (Brainstorm)**\n\n"
            "⚠️ Error: `sbtdd/spec-behavior-base.md` was not found. "
            "Run `/sbtdd-init` to scaffold it, then fill it in before proceeding."
        )

    try:
        actual_size = spec_base.stat().st_size
        with spec_base.open("rb") as f:
            raw = f.read(_MAX_SPEC_BYTES + 1)
        was_truncated = len(raw) > _MAX_SPEC_BYTES
        content = raw[:_MAX_SPEC_BYTES].decode("utf-8", errors="replace")
        if was_truncated:
            truncation_notice = (
                "\n\n⚠️ **Note:** spec-behavior-base.md exceeds safe size limit "
                f"({actual_size} bytes > {_MAX_SPEC_BYTES}). Content was truncated. "
                "Review and split into smaller specs if needed."
            )
        else:
            truncation_notice = ""
    except OSError as e:
        return (
            "# SBTDD Workflow\n\n"
            "**Phase: Specification (Brainstorm)**\n\n"
            f"⚠️ Error reading spec-behavior-base.md: {e}. "
            "Check file permissions and encoding, then run `/sbtdd` again."
        )

    open_fence, close_fence = _compute_fence(content)

    return f"""# SBTDD Workflow

**Phase: Specification (Brainstorm)**

The base spec is ready. Your task is to generate `sbtdd/spec-behavior.md` by refining and expanding `sbtdd/spec-behavior-base.md`.

## Input — spec-behavior-base.md

{open_fence}
{content}
{close_fence}
{truncation_notice}

## Instructions

1. **Read** the base spec above carefully.
2. **Refine** it into a full `sbtdd/spec-behavior.md` with this structure:
   - **Objective** — clear one-sentence feature description
   - **Requirements (SDD)** — SHALL statements, numbered, unambiguous
   - **Scenarios (BDD)** — Given / When / Then blocks for each acceptance test
   - **Constraints** — technical, performance, compatibility limits
   - **Non-goals** — explicitly out of scope to prevent creep
3. **Do NOT** include template markers (`<feature-name>`, `<!-- replace:`) in the output.
4. **Write** the result to `sbtdd/spec-behavior.md` using the appropriate file-writing tool.
5. **Verify** the file was created and contains no template markers.

## Rules
- Expand each bullet into concrete, testable statements.
- BDD scenarios must be atomic (one scenario per behavior).
- Every requirement MUST be traceable to at least one scenario.
- Constraints MUST be measurable (e.g., "response time < 200 ms" not "fast").

Next: After writing `sbtdd/spec-behavior.md`, run `/sbtdd` to proceed to planning.
"""


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
