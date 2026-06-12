"""
TDD: TDD-Guard override limit enforcement.

This test MUST fail before implementation (RED phase).
"""

from unittest.mock import patch

from sbtdd_hermes import _on_pre_tool_call
from sbtdd_hermes.state import SessionState, save_state
from sbtdd_hermes._config import MAX_OVERRIDE_PER_SESSION


class TestTDDGuardOverrideLimit:
    """RED: TDD-Guard must block after MAX_OVERRIDE_PER_SESSION overrides."""

    def test_override_count_increments_on_use(self, tmp_path, monkeypatch):
        """Using an override should increment tdd_guard_override_count."""
        # Use tmp_path as project root
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(
            current_phase="red",
            tdd_guard_override={"tool": "write_file", "path": "src/prod.py"},
            tdd_guard_override_count=0,
        )
        save_state(state_path, state, expected_revision=0)
        
        # Monkeypatch the hardcoded path in _on_pre_tool_call
        monkeypatch.chdir(project_dir)
        
        # Simulate pre_tool_call consuming the override
        result = _on_pre_tool_call("session-1", "write_file", {"path": "src/prod.py"})
        
        # Should be allowed
        assert result["blocked"] is False
        
        # Reload state
        from sbtdd_hermes.state import load_state
        new_state = load_state(state_path)
        assert new_state.tdd_guard_override_count == 1, \
            f"Expected override_count=1, got {new_state.tdd_guard_override_count}"
        assert new_state.tdd_guard_override == {}, \
            "Override should be consumed (one-shot)"

    def test_override_blocked_when_limit_reached(self, tmp_path, monkeypatch):
        """After MAX_OVERRIDE_PER_SESSION overrides, further overrides are blocked."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(
            current_phase="red",
            tdd_guard_override={"tool": "write_file", "path": "src/prod.py"},
            tdd_guard_override_count=MAX_OVERRIDE_PER_SESSION,  # Already at limit
        )
        save_state(state_path, state, expected_revision=0)
        
        monkeypatch.chdir(project_dir)
        
        result = _on_pre_tool_call("session-1", "write_file", {"path": "src/prod.py"})
        assert result["blocked"] is True, \
            f"Expected blocked=True when limit reached, got {result}"
        assert "limit" in result.get("reason", "").lower() or "exceeded" in result.get("reason", "").lower(), \
            f"Expected reason mentioning limit, got: {result.get('reason', '')}"

    def test_override_allowed_before_limit(self, tmp_path, monkeypatch):
        """Overrides should be allowed when count < MAX_OVERRIDE_PER_SESSION."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(
            current_phase="red",
            tdd_guard_override={"tool": "write_file", "path": "src/prod.py"},
            tdd_guard_override_count=MAX_OVERRIDE_PER_SESSION - 1,  # One left
        )
        save_state(state_path, state, expected_revision=0)
        
        monkeypatch.chdir(project_dir)
        
        result = _on_pre_tool_call("session-1", "write_file", {"path": "src/prod.py"})
        assert result["blocked"] is False, \
            f"Expected blocked=False when under limit, got {result}"

    def test_override_without_state_file_not_blocked(self):
        """If no state file exists, default behavior (no blocking)."""
        # Temporarily patch _get_cached_state to return default
        with patch("sbtdd_hermes._get_cached_state") as mock_get:
            mock_get.return_value = SessionState(
                current_phase="red",
                tdd_guard_override={"tool": "write_file"},
            )
            result = _on_pre_tool_call("session-1", "write_file", {"path": "src/prod.py"})
            assert result["blocked"] is False
