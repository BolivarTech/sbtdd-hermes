"""
Handlers for slash commands:
  /sbtdd
  /sbtdd-init
  /sbtdd-check
"""

from pathlib import Path

from . import prompts
from .scaffolding import (
    detect_stack,
    render_hermes_local_md,
    merge_gitignore,
    create_directories,
    seed_spec_behavior_base,
    scaffold_ollama_config,
)
from .state import load_state, SessionState


def _make_sbtdd_handler(ctx):
    def handler(args: str) -> str:
        state_path = Path(".hermes/session-state.json")
        state = load_state(state_path)
        
        if not state.current_task_id and state.current_phase == "red":
            return prompts.build_phase_prompt("red", state)
        
        return prompts.build_phase_prompt(state.current_phase, state)
    return handler


def _make_sbtdd_init_handler(ctx):
    def handler(args: str) -> str:
        root = Path(".")
        stack = detect_stack(root)
        
        # Generate HERMES.local.md
        hermes_md = render_hermes_local_md(stack)
        (root / "HERMES.local.md").write_text(hermes_md, encoding="utf-8")
        
        # Merge gitignore
        added, present, _ = merge_gitignore(root, [
            "/.hermes/",
            "/planning/",
            "/sbtdd/",
            "HERMES.local.md",
        ])
        
        # Create directories
        dirs = create_directories(root, ["sbtdd", "planning", ".hermes"])
        
        # Seed spec
        spec_path = seed_spec_behavior_base(root)
        
        # Summary table
        lines = [
            "# SBTDD Init Summary",
            "",
            f"| Item | Status |",
            f"|------|--------|",
            f"| Stack detected | {stack or 'unknown'} |",
            f"| HERMES.local.md | created |",
            f"| .gitignore entries | {len(added)} added, {len(present)} already present |",
            f"| Directories | {', '.join(dirs) or 'all exist'} |",
            f"| Spec base | {spec_path} |",
            "",
            "Next: Edit `sbtdd/spec-behavior-base.md` then run `/sbtdd` to begin.",
        ]
        return "\n".join(lines)
    return handler


def _make_sbtdd_check_handler(ctx):
    def handler(args: str) -> str:
        root = Path(".")
        checks = []
        
        # Check 1: HERMES.local.md exists
        hermes_exists = (root / "HERMES.local.md").exists()
        checks.append(("HERMES.local.md present", hermes_exists))
        
        # Check 2: Directories exist
        dirs_ok = all((root / d).exists() for d in ["sbtdd", "planning", ".hermes"])
        checks.append(("Directories (sbtdd, planning, .hermes)", dirs_ok))
        
        # Check 3: State file exists
        state_exists = (root / ".hermes" / "session-state.json").exists()
        checks.append(("Session state file", state_exists))
        
        # Check 4: Stack detected
        stack = detect_stack(root)
        checks.append(("Stack detected", bool(stack)))
        
        # Check 5: Git repo initialized
        git_exists = (root / ".git").exists()
        checks.append(("Git repository", git_exists))
        
        # Build table
        lines = ["# SBTDD Check Results", ""]
        lines.append("| Check | Status |")
        lines.append("|-------|--------|")
        for name, ok in checks:
            status = "✅ PASS" if ok else "❌ FAIL"
            lines.append(f"| {name} | {status} |")
        
        all_ok = all(ok for _, ok in checks)
        lines.append("")
        lines.append(f"**Overall: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}**")
        
        return "\n".join(lines)
    return handler


# Tool handlers

def _make_status_handler(ctx):
    def handler(args: dict) -> dict:
        state_path = Path(".hermes/session-state.json")
        state = load_state(state_path)
        return {
            "phase": state.current_phase,
            "task_id": state.current_task_id,
            "task_title": state.current_task_title,
            "magi_iterations": f"{state.magi_iterations_used}/{state.magi_iteration_budget}",
        }
    return handler


def _make_update_state_handler(ctx):
    def handler(args: dict) -> dict:
        from .validator import validate_full_update
        from .state import save_state, load_state
        
        state_path = Path(".hermes/session-state.json")
        current = load_state(state_path)
        
        field = args.get("field")
        value = args.get("value")
        expected_revision = args.get("expected_revision")
        
        if expected_revision is None:
            return {"ok": False, "error": "expected_revision is required"}
        
        ok, msg = validate_full_update(field, value, current)
        if not ok:
            return {"ok": False, "error": msg}
        
        import dataclasses
        new_state = dataclasses.replace(current, **{field: value})
        
        try:
            save_state(state_path, new_state, expected_revision=expected_revision)
            return {"ok": True, "new_revision": new_state.state_revision}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return handler
