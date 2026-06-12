"""
TDD: Ollama backend support in SessionState and sbtdd_status.

This test MUST fail before implementation (RED phase).
"""

import pytest
from unittest.mock import MagicMock

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState


class TestOllamaBackendInStatus:
    """RED: These tests verify that sbtdd_status reports magi_backend."""

    def test_session_state_has_magi_backend_field(self):
        """SessionState must have magi_backend field, default 'ollama'."""
        state = SessionState()
        assert hasattr(state, "magi_backend")
        assert state.magi_backend == "ollama"

    def test_sbtdd_status_reports_magi_backend(self):
        """sbtdd_status tool must include magi_backend in response."""
        ctx = MagicMock()
        register(ctx)
        
        # Find sbtdd_status handler
        status_call = None
        for call in ctx.register_tool.call_args_list:
            args = call.args if call.args else call.kwargs
            name = args[0] if isinstance(args, tuple) else args.get("name", call.args[0] if call.args else "")
            if name == "sbtdd_status":
                status_call = call
                break
        
        assert status_call is not None, "sbtdd_status tool not registered"
        
        # Get handler
        handler = status_call.kwargs.get("handler")
        if handler is None and len(status_call.args) >= 2:
            handler = status_call.args[1]
        
        assert handler is not None, "sbtdd_status handler not found"
        
        # Call handler
        result = handler({})
        assert "magi_backend" in result, f"magi_backend missing from status: {result}"
        assert result["magi_backend"] == "ollama"

    def test_magi_backend_is_whitelisted_for_update(self):
        """magi_backend must be updatable via sbtdd_update_state."""
        from sbtdd_hermes.validator import validate_update_field
        from sbtdd_hermes._config import STATE_UPDATE_FIELDS
        
        assert "magi_backend" in STATE_UPDATE_FIELDS, "magi_backend not in STATE_UPDATE_FIELDS"
        
        state = SessionState()
        ok, msg = validate_update_field("magi_backend", "openrouter", state)
        assert ok, f"magi_backend update rejected: {msg}"

    def test_magi_backend_choices_enforced(self):
        """Only allowed backends should be accepted."""
        from sbtdd_hermes.validator import validate_update_field
        
        state = SessionState()
        ok, msg = validate_update_field("magi_backend", "invalid_backend", state)
        assert ok is False, f"invalid backend should be rejected: {msg}"
        assert "choices" in msg.lower() or "not in" in msg.lower()


class TestOllamaInitFlag:
    """RED: /sbtdd-init --ollama should configure Ollama backend."""

    def test_init_command_accepts_ollama_flag(self):
        """/sbtdd-init should support --ollama flag."""
        ctx = MagicMock()
        register(ctx)
        
        # Find sbtdd-init handler
        init_call = None
        for call in ctx.register_command.call_args_list:
            name = call.args[0] if call.args else call.kwargs.get("command", "")
            if name == "sbtdd-init":
                init_call = call
                break
        
        assert init_call is not None, "sbtdd-init not registered"
        
        handler = init_call.kwargs.get("handler")
        if handler is None and len(init_call.args) >= 2:
            handler = init_call.args[1]
        
        assert handler is not None, "sbtdd-init handler not found"
        
        # Call with --ollama flag
        result = handler("--ollama")
        assert "ollama" in result.lower(), f"--ollama flag not recognized: {result}"

    def test_ollama_config_scaffolded_when_flag_present(self):
        """When --ollama is passed, Ollama config should be scaffolded."""
        # This is an integration test that will be implemented after
        # the unit tests pass.
        pytest.skip("Integration test for GREEN phase")
