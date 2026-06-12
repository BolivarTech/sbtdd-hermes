"""
TDD RED: filelock must be core dependency + TDD-Guard terminal fix.
These tests MUST fail before implementation (RED phase).
"""

import tomllib
from pathlib import Path
from unittest.mock import MagicMock


from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, save_state


class TestFilelockCoreDependency:
    """CRITICAL: filelock must be in [project.dependencies], not optional-dev."""

    def test_filelock_in_core_dependencies(self):
        pyproject = Path("pyproject.toml")
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        core = data["project"].get("dependencies", [])
        assert "filelock" in core, f"filelock must be core dependency, got: {core}"
        # Ensure NOT only in optional-dependencies
        optional = data["project"].get("optional-dependencies", {})
        dev = optional.get("dev", [])
        if dev:
            assert "filelock" not in dev, "filelock should not be dev-only"


class TestTDDGuardTerminalNotBlocked:
    """CRITICAL: terminal tool should not be blanket-blocked in RED phase."""

    def test_terminal_allowed_in_red_phase(self, tmp_path, monkeypatch):
        """Running pytest via terminal in RED should NOT be blocked."""
        monkeypatch.chdir(tmp_path)
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)

        ctx = MagicMock()
        register(ctx)

        # Get the hook handler
        hook_calls = [c for c in ctx.register_hook.call_args_list if c.args[0] == "pre_tool_call"]
        assert len(hook_calls) == 1, "pre_tool_call hook not registered"
        hook = hook_calls[0].args[1]

        # Simulate terminal call with pytest command (typical RED phase usage)
        result = hook(
            session_id="test-session",
            tool_name="terminal",
            tool_args={"command": "pytest tests/test_foo.py -v"},
        )
        assert result["blocked"] is False, (
            f"terminal running pytest should be allowed in RED, got: {result}"
        )

    def test_terminal_git_status_allowed_in_red(self, tmp_path, monkeypatch):
        """Read-only terminal calls (git status) should NOT be blocked in RED."""
        monkeypatch.chdir(tmp_path)
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)

        ctx = MagicMock()
        register(ctx)

        hook_calls = [c for c in ctx.register_hook.call_args_list if c.args[0] == "pre_tool_call"]
        hook = hook_calls[0].args[1]

        result = hook(
            session_id="test-session",
            tool_name="terminal",
            tool_args={"command": "git status --short"},
        )
        assert result["blocked"] is False, (
            f"terminal read-only (git status) should be allowed in RED, got: {result}"
        )
