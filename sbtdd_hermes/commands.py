"""
Handlers for slash commands:
  /sbtdd
  /sbtdd-init
  /sbtdd-check
  /sbtdd-override
"""

from pathlib import Path

from .state import load_state, save_state
from .scaffolding import (
    detect_stack,
    render_hermes_local_md,
    merge_gitignore,
    create_directories,
    seed_spec_behavior_base,
    scaffold_ollama_config,
)
from . import _config
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
        
        # Parse --ollama flag
        use_ollama = "--ollama" in args.split() if args else False
        
        # Generate HERMES.local.md with Ollama backend if requested
        backend = "ollama" if use_ollama else "ollama"  # default to ollama
        hermes_md = render_hermes_local_md(stack, backend=backend)
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
        
        # Ollama scaffolding if requested
        ollama_msg = ""
        if use_ollama:
            ollama_msg = "\n- Ollama backend configured (default)"
        
        # Summary table
        lines = [
            "# SBTDD Init Summary",
            "",
            f"| Item | Status |",
            f"|------|--------|",
            f"| Stack detected | {stack or 'unknown'} |",
            f"| HERMES.local.md | created |",
            f"| MAGI backend | {backend} |",
            f"| .gitignore entries | {len(added)} added, {len(present)} already present |",
            f"| Directories | {', '.join(dirs) or 'all exist'} |",
            f"| Spec base | {spec_path} |",
            f"| Ollama | {'enabled' if use_ollama else 'default'} |",
            "",
            "Next: Edit `sbtdd/spec-behavior-base.md` then run `/sbtdd` to begin.",
        ]
        return "\n".join(lines)
    return handler


def _make_sbtdd_override_handler(ctx):
    def handler(args: str) -> str:
        import re
        state_path = Path(".hermes/session-state.json")
        
        # Parse arguments: --tool TOOL [--path PATH] [--reason REASON]
        tool_match = re.search(r"--tool\s+(\S+)", args)
        path_match = re.search(r"--path\s+(\S+)", args)
        reason_match = re.search(r"--reason\s+(.+?)(?=\s+--|$)", args)
        
        if not tool_match:
            return "Error: --tool is required. Usage: /sbtdd-override --tool write_file [--path src/prod.py] [--reason \"explanation\"]"
        
        tool = tool_match.group(1)
        path = path_match.group(1) if path_match else None
        reason = reason_match.group(1) if reason_match else ""
        
        # Load state
        state = load_state(state_path)
        
        # Check limit
        if state.tdd_guard_override_count >= 3:
            return f"Error: Override limit exceeded ({state.tdd_guard_override_count}/3)."
        
        # Set override
        override = {"tool": tool}
        if path:
            override["path"] = path
        if reason:
            override["reason"] = reason
        
        import dataclasses
        new_state = dataclasses.replace(state, tdd_guard_override=override)
        
        try:
            save_state(state_path, new_state, expected_revision=state.state_revision)
            return f"Override set for tool '{tool}'" + (f" on path '{path}'" if path else "") + f". Used {state.tdd_guard_override_count}/3."
        except Exception as e:
            return f"Error saving state: {e}"
    
    return handler


def _make_sbtdd_check_handler(ctx):
    def handler(args: str) -> str:
        root = Path(".")
        checks = []
        warnings_list = []
        
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
        if state_exists:
            state = load_state(state_path)
            backend = state.magi_backend
            backend_ok = backend in _config.STATE_UPDATE_FIELDS.get("magi_backend", {}).get("choices", set())
            if not backend_ok:
                warnings_list.append(f"Invalid MAGI backend '{backend}' (expected: ollama, openrouter, claude, openai)")
        checks.append((f"MAGI backend ({backend})", backend_ok))
        
        # Check 5: Stack detected
        stack = detect_stack(root)
        checks.append(("Stack detected", bool(stack)))
        
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

def _make_status_handler(ctx):
    def handler(args: dict) -> dict:
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
