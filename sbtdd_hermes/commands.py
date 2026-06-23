"""
Handlers for slash commands:
  /sbtdd
  /sbtdd-init
  /sbtdd-check
  /sbtdd-override
"""

from typing import Any
from pathlib import Path
import json

from . import _config, prompts
from .state import load_state, save_state, SessionState
from .scaffolding import (
    detect_stack,
    render_hermes_local_md,
    merge_gitignore,
    create_directories,
    seed_spec_behavior_base,
)
from .prompts import build_brainstorm_prompt


def _make_sbtdd_handler(ctx: Any) -> Any:
    def handler(args: str) -> str:
        root = Path(".")
        phase, message = _determine_phase(root)

        if phase == "specification_edit":
            return (
                "# SBTDD Workflow\n\n"
                "**Phase: Specification (Edit)**\n\n"
                f"{message}\n\n"
                "Next: Once the spec base is ready, run `/sbtdd` to begin brainstorming."
            )

        if phase == "specification_brainstorm":
            return (
                "Phase: Specification (Brainstorm)\n\n"
                "The spec base is ready at `sbtdd/spec-behavior-base.md`.\n\n"
                "ACTION REQUIRED: Tell the agent to refine it. For example:\n"
                "  'Read sbtdd/spec-behavior-base.md and write a refined spec to sbtdd/spec-behavior.md'\n\n"
                "The refined spec must have: Objective, Requirements (SDD), "
                "Scenarios (BDD), Constraints, Non-goals.\n\n"
                "After the file is written, run `/sbtdd` to proceed to planning."
            )

        if phase == "planning":
            return (
                "# SBTDD Workflow\n\n"
                "**Phase: Planning**\n\n"
                f"{message}\n\n"
                "Next: After the plan is created, run `/sbtdd` to proceed to the plan gate."
            )

        if phase == "plan_gate":
            return (
                "# SBTDD Workflow\n\n"
                "**Phase: Plan Gate (Checkpoint 1 → Checkpoint 2)**\n\n"
                f"{message}\n\n"
                "Next: After MAGI approves the plan, run `/sbtdd` to begin execution."
            )

        if phase == "pre_merge":
            return (
                "# SBTDD Workflow\n\n"
                "**Phase: Pre-Merge Review**\n\n"
                f"{message}\n\n"
                "Next: Run `/sbtdd-check` to verify state, then proceed to merge."
            )

        # Execution phases: red, green, refactor, done
        state_path = root / ".hermes" / "session-state.json"
        if not state_path.exists():
            return (
                "Error: No session state found. Run `/sbtdd-init` to initialize, "
                "or `/sbtdd-check` to verify setup."
            )
        state = load_state(state_path)
        return prompts.build_phase_prompt(phase, state)

    return handler


def _has_template_markers(path: Path) -> bool:
    """Check if spec-behavior-base.md still has template markers.

    Returns True (treat as incomplete) when the file is missing or unreadable.
    This is a fail-open strategy: if we can't verify the spec is clean, we ask
    the user to fill it in before proceeding.
    """
    if not path.exists():
        return True
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True
    return "<!-- replace:" in content or "<feature-name>" in content or "<actor>" in content


def _determine_phase(root: Path) -> tuple[str, str | None]:
    """Determine the current SBTDD phase based on artifacts (per routing.md)."""
    spec_base = root / "sbtdd" / "spec-behavior-base.md"
    spec = root / "sbtdd" / "spec-behavior.md"
    plan_org = root / "planning" / "hermes-plan-tdd-org.md"
    plan = root / "planning" / "hermes-plan-tdd.md"
    state_path = root / ".hermes" / "session-state.json"

    # Check 1: spec-behavior-base.md missing or has markers
    if not spec_base.exists() or _has_template_markers(spec_base):
        return "specification_edit", (
            "spec-behavior-base.md is missing or still contains template markers. "
            "Please fill it in before proceeding."
        )

    # Check 2: spec-behavior.md absent — spec-base is ready, start brainstorm
    if not spec.exists():
        return "specification_brainstorm", None

    # Check 3: plan absent
    if not plan_org.exists() and not plan.exists():
        return "planning", (
            "No plan found. Use `/skill plan` to create planning/hermes-plan-tdd-org.md."
        )

    # Check 4: plan-org present but approved plan absent
    if plan_org.exists() and not plan.exists():
        return "plan_gate", (
            "planning/hermes-plan-tdd-org.md exists but has not been approved yet. "
            "Review it manually (Checkpoint 1), then run MAGI (Checkpoint 2)."
        )

    # Check 5: Approved plan exists
    if plan.exists():
        if not plan_org.exists():
            return "plan_gate", (
                "planning/hermes-plan-tdd.md exists but planning/hermes-plan-tdd-org.md is missing. "
                "This suggests the plan gate was bypassed. Please review the plan manually before proceeding."
            )
        if state_path.exists():
            state = load_state(state_path)
            if state.current_phase == "done":
                return "pre_merge", ("All tasks complete. Proceed to pre-merge review.")
            # Validate phase is a known execution phase
            if state.current_phase not in {"red", "green", "refactor"}:
                return "red", (
                    f"Invalid phase '{state.current_phase}' in state. "
                    "Resetting to red. Run `/sbtdd` to continue."
                )
            return state.current_phase, None
        else:
            # No state file but approved plan exists -> start execution at red
            return "red", None

    return "red", None


def _make_sbtdd_init_handler(ctx: Any) -> Any:
    def handler(args: str) -> str:
        root = Path(".")
        stack = detect_stack(root)

        # Parse --ollama-init flag (per spec)
        use_ollama = "--ollama-init" in args.split() if args else False

        # Backend is always ollama by default; --ollama-init triggers magi-ollama.toml scaffolding
        backend = "ollama"
        hermes_md = render_hermes_local_md(stack, backend=backend)
        (root / "HERMES.local.md").write_text(hermes_md, encoding="utf-8")

        # Merge gitignore
        added, present, _ = merge_gitignore(
            root,
            [
                "/.hermes/",
                "/planning/",
                "/sbtdd/",
                "HERMES.local.md",
            ],
        )

        # Create directories
        dirs = create_directories(root, ["sbtdd", "planning", ".hermes"])

        # Seed spec
        spec_path = seed_spec_behavior_base(root)

        # Create session state file
        state_path = root / ".hermes" / "session-state.json"
        state = SessionState(magi_backend=backend, stack=stack)
        state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

        # Summary table
        lines = [
            "# SBTDD Init Summary",
            "",
            "| Item | Status |",
            "|------|--------|",
            f"| Stack detected | {stack or 'unknown'} |",
            "| HERMES.local.md | created |",
            f"| MAGI backend | {backend} |",
            f"| .gitignore entries | {len(added)} added, {len(present)} already present |",
            f"| Directories | {', '.join(dirs) or 'all exist'} |",
            f"| Spec base | {spec_path} |",
            f"| Session state | {state_path} |",
            f"| Ollama | {'enabled' if use_ollama else 'default'} |",
            "",
            "Next: Edit `sbtdd/spec-behavior-base.md` then run `/sbtdd` to begin.",
        ]
        return "\n".join(lines)

    return handler


def _make_sbtdd_override_handler(ctx: Any) -> Any:
    def handler(args: str) -> str:
        import re

        state_path = Path(".hermes/session-state.json")

        # Parse arguments: --tool TOOL [--path PATH] [--reason REASON]
        tool_match = re.search(r"--tool\s+(\S+)", args)
        path_match = re.search(r"--path\s+(\S+)", args)
        reason_match = re.search(r"--reason\s+(.+?)(?=\s+--|$)", args)

        if not tool_match:
            return 'Error: --tool is required. Usage: /sbtdd-override --tool write_file [--path src/prod.py] [--reason "explanation"]'

        tool = tool_match.group(1)
        path = path_match.group(1) if path_match else None
        reason = reason_match.group(1) if reason_match else ""

        # Load state
        if not state_path.exists():
            return "Error: No session state found. Run `/sbtdd-init` first."
        state = load_state(state_path)

        # Check limit
        if state.tdd_guard_override_count >= 3:
            return f"Error: Override limit exceeded ({state.tdd_guard_override_count}/3)."

        # Set override
        override: dict[str, Any] = {"tool": tool}
        if path:
            override["path"] = path
        if reason:
            override["reason"] = reason

        import dataclasses

        new_state = dataclasses.replace(state, tdd_guard_override=override)

        try:
            save_state(state_path, new_state, expected_revision=state.state_revision)
            return (
                f"Override set for tool '{tool}'"
                + (f" on path '{path}'" if path else "")
                + f". Used {state.tdd_guard_override_count}/3."
            )
        except Exception as e:
            return f"Error saving state: {e}"

    return handler


def _make_sbtdd_check_handler(ctx: Any) -> Any:
    def handler(args: str) -> str:
        root = Path(".")
        checks: list[tuple[str, bool]] = []
        warnings_list: list[str] = []

        # Check 1: HERMES.local.md exists
        hermes_exists = (root / "HERMES.local.md").exists()
        checks.append(("HERMES.local.md present", hermes_exists))

        # Check 2: Directories exist
        dirs_ok = all((root / d).exists() for d in ["sbtdd", "planning", ".hermes"])
        checks.append(("Directories (sbtdd, planning, .hermes)", dirs_ok))

        # Check 3: State file exists
        state_path = root / ".hermes" / "session-state.json"
        state_exists = state_path.exists()
        checks.append(("Session state file", state_exists))

        # Check 4: MAGI backend config
        backend = "unknown"
        backend_ok = False
        stack = None
        if state_exists:
            state = load_state(state_path)
            backend = state.magi_backend
            stack = state.stack
            backend_cfg = _config.STATE_UPDATE_FIELDS.get("magi_backend", {})
            choices = backend_cfg.get("choices", set())
            backend_ok = backend in choices  # type: ignore[operator]
            if not backend_ok:
                warnings_list.append(
                    f"Invalid MAGI backend '{backend}' (expected: ollama, openrouter, claude, openai)"
                )
        checks.append((f"MAGI backend ({backend})", backend_ok))

        # Check 5: Stack detected
        if stack is None:
            stack = detect_stack(root)
        checks.append((f"Stack detected ({stack or 'none'})", bool(stack)))

        # Check 6: Git repo initialized
        git_exists = (root / ".git").exists()
        checks.append(("Git repository", git_exists))

        # Build table
        lines = ["# SBTDD Check Results", ""]
        lines.append("| Check | Status |")
        lines.append("|-------|--------|")
        for name, ok in checks:
            status = "✅ PASS" if ok else "❌ FAIL"
            lines.append(f"| {name} | {status} |")

        # Add warnings
        if warnings_list:
            lines.append("")
            lines.append("## Warnings")
            for w in warnings_list:
                lines.append(f"- ⚠️ {w}")

        all_ok = all(ok for _, ok in checks)
        lines.append("")
        lines.append(f"**Overall: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}**")

        return "\n".join(lines)

    return handler


# Tool handlers


def _make_status_handler(ctx: Any) -> Any:
    def handler(args: dict[str, Any]) -> dict[str, Any]:
        state_path = Path(".hermes/session-state.json")
        state = load_state(state_path)
        return {
            "phase": state.current_phase,
            "task_id": state.current_task_id,
            "task_title": state.current_task_title,
            "magi_iterations": f"{state.magi_iterations_used}/{state.magi_iteration_budget}",
            "magi_backend": state.magi_backend,
        }

    return handler


def _make_update_state_handler(ctx: Any) -> Any:
    def handler(args: dict[str, Any]) -> dict[str, Any]:
        from .validator import validate_full_update
        from .state import save_state, load_state

        state_path = Path(".hermes/session-state.json")
        current = load_state(state_path)

        field = args.get("field")
        value = args.get("value")
        expected_revision = args.get("expected_revision")

        if expected_revision is None:
            return {"ok": False, "error": "expected_revision is required"}

        ok, msg = validate_full_update(str(field), value, current)
        if not ok:
            return {"ok": False, "error": msg}

        import dataclasses

        new_state = dataclasses.replace(current, **{str(field): value})  # type: ignore[arg-type]

        try:
            save_state(state_path, new_state, expected_revision=expected_revision)
            return {"ok": True, "new_revision": new_state.state_revision}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return handler
