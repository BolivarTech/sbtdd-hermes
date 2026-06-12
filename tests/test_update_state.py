"""
TDD: sbtdd_update_state robustness.

This test MUST fail before implementation (RED phase).
"""

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, load_state, save_state


class TestSBTDDUpdateStateRobustness:
    """RED: sbtdd_update_state must validate inputs and handle errors."""

    def test_update_state_creates_new_when_missing(self, tmp_path, monkeypatch):
        """When no state file exists, should create one and succeed."""
        monkeypatch.chdir(tmp_path)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_update_state":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None, "sbtdd_update_state handler not found"
        
        # No state file exists yet
        result = handler({"field": "current_phase", "value": "green", "expected_revision": 0})
        # Should create state and succeed
        assert result["ok"] is True, f"Expected ok=True for fresh state, got {result}"
        assert "new_revision" in result
        
        # Verify state created
        state_path = tmp_path / ".hermes" / "session-state.json"
        assert state_path.exists(), "State file should be created"
        new_state = load_state(state_path)
        assert new_state.current_phase == "green"

    def test_update_state_requires_expected_revision(self, tmp_path, monkeypatch):
        """expected_revision is mandatory for OCC."""
        monkeypatch.chdir(tmp_path)
        
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_update_state":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        result = handler({"field": "current_phase", "value": "green"})
        assert result["ok"] is False
        assert "expected_revision" in result.get("error", "").lower()

    def test_update_state_applies_valid_field(self, tmp_path, monkeypatch):
        """Valid field update should succeed and return new revision."""
        monkeypatch.chdir(tmp_path)
        
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)
        
        # After save, state_revision in file is 1
        current_revision = load_state(state_path).state_revision
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_update_state":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        result = handler({"field": "current_phase", "value": "green", "expected_revision": current_revision})
        assert result["ok"] is True, f"Expected ok=True, got: {result}"
        assert "new_revision" in result, f"new_revision missing from: {result}"
        assert result["new_revision"] == current_revision + 1
        
        # Verify state persisted
        new_state = load_state(state_path)
        assert new_state.current_phase == "green"
        assert new_state.state_revision == current_revision + 1

    def test_update_state_rejects_invalid_value(self, tmp_path, monkeypatch):
        """Invalid value should fail without changing state."""
        monkeypatch.chdir(tmp_path)
        
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)
        
        current_revision = load_state(state_path).state_revision
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_update_state":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        # Invalid transition: red -> refactor
        result = handler({"field": "current_phase", "value": "refactor", "expected_revision": current_revision})
        assert result["ok"] is False, f"Expected ok=False for invalid transition, got: {result}"
        
        # Verify state NOT changed
        new_state = load_state(state_path)
        assert new_state.current_phase == "red"
        assert new_state.state_revision == current_revision
