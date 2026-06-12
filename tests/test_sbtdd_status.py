"""
TDD: sbtdd_status tool schema and response.

This test MUST fail before implementation (RED phase).
"""

from unittest.mock import MagicMock

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, save_state


class TestSBTDDStatusTool:
    """RED: sbtdd_status must have proper schema and complete response."""

    def test_status_schema_has_properties(self):
        """sbtdd_status schema must declare output properties."""
        ctx = MagicMock()
        register(ctx)
        
        schema = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_status":
                schema = call.kwargs.get("schema")
                break
        
        assert schema is not None, "sbtdd_status schema not found"
        assert schema.get("type") == "object", "Schema must be object type"
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Must declare phase property
        assert "phase" in properties, f"phase not in schema properties: {properties.keys()}"
        assert properties["phase"].get("type") == "string"
        assert "phase" in required, "phase should be required"

    def test_status_schema_declares_all_fields(self):
        """Schema must declare all response fields."""
        ctx = MagicMock()
        register(ctx)
        
        schema = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_status":
                schema = call.kwargs.get("schema")
                break
        
        properties = schema.get("properties", {})
        
        expected_fields = ["phase", "task_id", "task_title", "magi_iterations", "magi_backend"]
        for field in expected_fields:
            assert field in properties, f"{field} not declared in schema"

    def test_status_response_includes_all_fields(self, tmp_path, monkeypatch):
        """Handler response must include all documented fields."""
        monkeypatch.chdir(tmp_path)
        
        hermes_dir = tmp_path / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(
            current_phase="green",
            current_task_id="T-42",
            current_task_title="Test feature",
            magi_backend="ollama",
            magi_iterations_used=2,
            magi_iteration_budget=5,
        )
        save_state(state_path, state, expected_revision=0)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_status":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None
        
        result = handler({})
        
        # All fields present
        assert result.get("phase") == "green"
        assert result.get("task_id") == "T-42"
        assert result.get("task_title") == "Test feature"
        assert result.get("magi_backend") == "ollama"
        assert "magi_iterations" in result
        assert result["magi_iterations"] == "2/5"

    def test_status_response_with_defaults(self, tmp_path, monkeypatch):
        """Handler response with default/empty state."""
        monkeypatch.chdir(tmp_path)
        
        # No state file = default state
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_tool.call_args_list:
            if call.args[0] == "sbtdd_status":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        result = handler({})
        
        assert result.get("phase") == "red"  # default
        assert result.get("magi_backend") == "ollama"  # default
