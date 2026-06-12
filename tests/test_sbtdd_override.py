"""
TDD: /sbtdd-override command to set TDD-Guard override.

This test MUST fail before implementation (RED phase).
"""

from unittest.mock import MagicMock

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, load_state, save_state


class TestSBTDDOverrideCommand:
    """RED: /sbtdd-override must register and set tdd_guard_override in state."""

    def test_override_command_is_registered(self):
        """Plugin must register /sbtdd-override command."""
        ctx = MagicMock()
        register(ctx)
        
        names = [call.args[0] for call in ctx.register_command.call_args_list]
        assert "sbtdd-override" in names, f"Commands registered: {names}"

    def test_override_sets_tdd_guard_override(self, tmp_path, monkeypatch):
        """/sbtdd-override must set tdd_guard_override in state file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)
        
        monkeypatch.chdir(project_dir)
        
        # DEBUG: Verify state file exists
        assert state_path.exists(), f"State file not created at {state_path}"
        
        ctx = MagicMock()
        register(ctx)
        
        # Find sbtdd-override handler
        handler = None
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd-override":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None, "sbtdd-override handler not found"
        
        # Call with tool and path
        result = handler("--tool write_file --path src/prod.py")
        
        # DEBUG: Print result
        print(f"\nHandler result: {result}")
        print(f"State path: {state_path}")
        print(f"State exists after: {state_path.exists()}")
        if state_path.exists():
            import json
            print(f"Raw state file: {json.loads(state_path.read_text())}")
        
        # Verify state updated
        new_state = load_state(state_path)
        print(f"Loaded state tdd_guard_override: {new_state.tdd_guard_override}")
        assert new_state.tdd_guard_override.get("tool") == "write_file"
        assert new_state.tdd_guard_override.get("path") == "src/prod.py"

    def test_override_requires_tool_argument(self, tmp_path, monkeypatch):
        """/sbtdd-override without --tool should fail."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red")
        save_state(state_path, state, expected_revision=0)
        
        monkeypatch.chdir(project_dir)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd-override":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None
        
        # Call without --tool
        result = handler("--path src/prod.py")
        assert "error" in result.lower() or "tool" in result.lower()

    def test_override_increments_count(self, tmp_path, monkeypatch):
        """Each override call should increment override_count."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        hermes_dir = project_dir / ".hermes"
        hermes_dir.mkdir()
        state_path = hermes_dir / "session-state.json"
        
        state = SessionState(current_phase="red", tdd_guard_override_count=2)
        save_state(state_path, state, expected_revision=0)
        
        monkeypatch.chdir(project_dir)
        
        ctx = MagicMock()
        register(ctx)
        
        handler = None
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd-override":
                handler = call.kwargs.get("handler") or call.args[1]
                break
        
        assert handler is not None
        
        handler("--tool write_file --path src/prod.py")
        
        new_state = load_state(state_path)
        assert new_state.tdd_guard_override_count == 2  # Don't increment on SET, only on USE
