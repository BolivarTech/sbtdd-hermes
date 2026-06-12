"""
TDD: sbtdd-check verifies MAGI backend configuration.

This test MUST fail before implementation (RED phase).
"""

from unittest.mock import MagicMock

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, save_state


class TestSBTDDCheckBackend:
    """RED: /sbtdd-check must verify MAGI backend config in state."""

    def test_check_reports_magi_backend(self, tmp_path, monkeypatch):
        """sbtdd-check output should include magi_backend status."""
        monkeypatch.chdir(tmp_path)
        
        # Create state with backend
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        state = SessionState(magi_backend="ollama")
        save_state(state_path, state, expected_revision=0)
        
        # Also create minimal required files
        (tmp_path / "HERMES.local.md").write_text("# Test")
        (tmp_path / "sbtdd").mkdir(exist_ok=True)
        (tmp_path / "planning").mkdir(exist_ok=True)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd-check":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None, "sbtdd-check handler not found"
        
        result = handler("")
        assert "ollama" in result.lower() or "magi_backend" in result.lower(), \
            f"Expected backend info in check output: {result[:200]}"

    def test_check_warns_on_unsupported_backend(self, tmp_path, monkeypatch):
        """sbtdd-check should warn if backend not in allowed list."""
        monkeypatch.chdir(tmp_path)
        
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        state = SessionState(magi_backend="unsupported_xyz")
        save_state(state_path, state, expected_revision=0)
        
        (tmp_path / "HERMES.local.md").write_text("# Test")
        (tmp_path / "sbtdd").mkdir(exist_ok=True)
        (tmp_path / "planning").mkdir(exist_ok=True)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd-check":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        result = handler("")
        # Should contain warning about invalid backend
        assert any(word in result.lower() for word in ["warn", "invalid", "unsupported", "backend"]), \
            f"Expected warning for invalid backend: {result[:300]}"
