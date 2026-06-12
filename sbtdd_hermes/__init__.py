"""
SBTDD-Hermes Plugin for Hermes Agent
Entry point: register(ctx)
"""

import dataclasses
import re
from pathlib import Path

from . import _config
from .state import load_state, save_state, SessionState
from .commands import (
    _make_sbtdd_handler,
    _make_sbtdd_init_handler,
    _make_sbtdd_check_handler,
    _make_sbtdd_override_handler,
    _make_status_handler,
    _make_update_state_handler,
)

# Cache de estado: {session_id: (state, mtime_ns)}
_state_cache: dict[str, tuple[SessionState, int]] = {}


def register(ctx):
    """Register plugin commands, tools, and hooks."""
    ctx.register_command("sbtdd", handler=_make_sbtdd_handler(ctx))
    ctx.register_command("sbtdd-init", handler=_make_sbtdd_init_handler(ctx))
    ctx.register_command("sbtdd-check", handler=_make_sbtdd_check_handler(ctx))
    ctx.register_command("sbtdd-override", handler=_make_sbtdd_override_handler(ctx))

    ctx.register_tool(
        "sbtdd_status",
        schema={
            "type": "object",
            "properties": {
                "phase": {"type": "string", "description": "Current TDD phase (red, green, refactor, done)"},
                "task_id": {"type": ["string", "null"], "description": "Current task identifier"},
                "task_title": {"type": ["string", "null"], "description": "Current task title"},
                "magi_iterations": {"type": "string", "description": "MAGI iterations used/budget"},
                "magi_backend": {"type": "string", "description": "MAGI backend (ollama, openrouter, claude, openai)"},
            },
            "required": ["phase", "magi_backend"],
        },
        handler=_make_status_handler(ctx),
    )
    ctx.register_tool(
        "sbtdd_update_state",
        schema={
            "type": "object",
            "properties": {
                "field": {"type": "string"},
                "value": {},
                "expected_revision": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["field", "value", "expected_revision"],
        },
        handler=_make_update_state_handler(ctx),
    )

    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("on_session_start", _on_session_start)


def _get_cached_state(session_id: str, path: Path) -> SessionState:
    """Lee state con cache basado en mtime_ns."""
    if session_id in _state_cache:
        cached_state, cached_mtime = _state_cache[session_id]
        current_mtime = path.stat().st_mtime_ns if path.exists() else 0
        if current_mtime == cached_mtime:
            return cached_state
    state = load_state(path)
    mtime = path.stat().st_mtime_ns if path.exists() else 0
    _state_cache[session_id] = (state, mtime)
    return state


def _is_test_file(path: str) -> bool:
    """Heuristica: determina si un path es archivo de test."""
    for pattern in _config.TDDGUARD_TEST_PATTERNS:
        if re.search(pattern, path):
            return True
    return False


def _on_pre_tool_call(session_id, tool_name, tool_args, **kwargs):
    """Hook TDD-Guard: bloquea writes violatorios segun fase."""
    if tool_name not in _config.TDDGUARD_TOOL_NAMES:
        return {"blocked": False}

    state_path = Path(".hermes/session-state.json")
    if not state_path.exists():
        return {"blocked": False}

    state = _get_cached_state(session_id, state_path)

    # Check override scoped
    override = state.tdd_guard_override
    if override and override.get("tool") == tool_name:
        # Check limit FIRST
        if state.tdd_guard_override_count >= _config.MAX_OVERRIDE_PER_SESSION:
            return {
                "blocked": True,
                "reason": (
                    f"TDD-Guard override limit exceeded "
                    f"({state.tdd_guard_override_count}/{_config.MAX_OVERRIDE_PER_SESSION})."
                ),
            }
        
        if "path" in override:
            tool_path = tool_args.get("path", "")
            if tool_path != override["path"]:
                return {"blocked": True, "reason": "Override scoped to different path"}

        # Consumir override (one-shot) + incrementar count
        new_state = dataclasses.replace(
            state,
            tdd_guard_override={},
            tdd_guard_override_count=state.tdd_guard_override_count + 1,
            last_override_reason=override.get("reason", ""),
        )
        try:
            save_state(state_path, new_state, expected_revision=state.state_revision)
        except Exception:
            pass  # Don't block tool if save fails
        return {"blocked": False}

    # TDD phase enforcement
    phase = state.current_phase

    if phase == "red":
        # Only test files allowed
        path = tool_args.get("path", "")
        if path and not _is_test_file(path):
            return {
                "blocked": True,
                "reason": (
                    f"TDD-RED: Cannot write production code ({path}). "
                    f"Write tests only (test_*.py or in tests/). "
                    f"Use --override-guard if this is intentional."
                ),
            }
        return {"blocked": False}

    elif phase == "green":
        # Don't modify tests in green phase
        path = tool_args.get("path", "")
        if path and _is_test_file(path):
            return {
                "blocked": True,
                "reason": (
                    f"TDD-GREEN: Cannot modify tests ({path}). "
                    f"Write production code only."
                ),
            }
        return {"blocked": False}

    elif phase == "refactor":
        # Allow everything but warn about new features
        return {"blocked": False, "warning": "TDD-REFACTOR: Ensure no new functionality is added"}

    elif phase == "done":
        return {"blocked": False}

    return {"blocked": False}


def _on_session_start(session_id, **kwargs):
    """Hook de sesion: inicializa estado si existe plan."""
    state_path = Path(".hermes/session-state.json")
    if state_path.exists():
        state = load_state(state_path)
        if state.current_task_id or state.current_phase != "red":
            return f"SBTDD: Resuming task '{state.current_task_title}' in phase '{state.current_phase}'"
    return None
