"""
TDD: /sbtdd handler routing behavior per routing.md.

This test MUST fail before implementation (RED phase).
"""

from unittest.mock import MagicMock

from sbtdd_hermes import register
from sbtdd_hermes.state import SessionState, save_state


class TestSBTDDRouting:
    """RED: /sbtdd must route to the correct phase based on artifacts."""

    def _get_handler(self, ctx):
        """Extract the sbtdd command handler from registered commands."""
        for call in ctx.register_command.call_args_list:
            if call.args[0] == "sbtdd":
                return call.kwargs.get("handler") or call.args[1]
        raise AssertionError("sbtdd handler not found")

    def test_routes_to_specification_when_spec_base_has_markers(self, tmp_path, monkeypatch):
        """When spec-behavior-base.md has template markers, route to specification."""
        monkeypatch.chdir(tmp_path)

        # Create init artifacts
        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Create spec-behavior-base.md with template markers
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec-Behavior Base\n\n<!-- replace: short project name -->\n**Feature:** `<feature-name>`"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification" in result, f"Expected specification phase, got: {result}"
        assert "template markers" in result.lower() or "fill it in" in result.lower()

    def test_routes_to_specification_when_spec_behavior_missing(self, tmp_path, monkeypatch):
        """When spec-behavior-base.md is filled but spec-behavior.md missing, route to specification."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Create spec-behavior-base.md WITHOUT template markers
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec-Behavior Base\n\n**Feature:** MyFeature\n\n## Objective\n> This feature allows users to do X."
        )

        # No spec-behavior.md

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification" in result, f"Expected specification phase, got: {result}"
        assert "spec-behavior.md" in result.lower()

    def test_routes_to_planning_when_no_plan(self, tmp_path, monkeypatch):
        """When spec exists but no plan, route to planning."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Both specs exist, no plan
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base\n\n**Feature:** X")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec\n\nDone.")

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Planning" in result, f"Expected planning phase, got: {result}"
        assert "/skill plan" in result.lower() or "plan" in result.lower()

    def test_routes_to_plan_gate_when_org_plan_exists(self, tmp_path, monkeypatch):
        """When org plan exists but approved plan does not, route to plan gate."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec")
        (tmp_path / "planning" / "hermes-plan-tdd-org.md").write_text("# Org Plan")
        # No hermes-plan-tdd.md

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Plan Gate" in result, f"Expected plan gate phase, got: {result}"
        assert "checkpoint" in result.lower() or "magi" in result.lower()

    def test_routes_to_red_when_approved_plan_exists(self, tmp_path, monkeypatch):
        """When approved plan exists and state is red, route to execution/red."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec")
        (tmp_path / "planning" / "hermes-plan-tdd-org.md").write_text("# Org Plan")
        (tmp_path / "planning" / "hermes-plan-tdd.md").write_text("# Approved Plan")

        # State file with red phase
        state = SessionState(
            current_phase="red", current_task_id="T-1", current_task_title="First task"
        )
        state_path = tmp_path / ".hermes" / "session-state.json"
        save_state(state_path, state, expected_revision=0)

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "TDD-RED" in result, f"Expected TDD-RED phase, got: {result}"
        assert "First task" in result or "test:" in result.lower()

    def test_routes_to_error_when_approved_plan_but_no_state(self, tmp_path, monkeypatch):
        """When approved plan exists but no state file, return error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec")
        (tmp_path / "planning" / "hermes-plan-tdd-org.md").write_text("# Org Plan")
        (tmp_path / "planning" / "hermes-plan-tdd.md").write_text("# Approved Plan")

        # NO state file

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Error" in result, f"Expected error, got: {result}"
        assert "/sbtdd-init" in result or "/sbtdd-check" in result

    def test_routes_to_pre_merge_when_done(self, tmp_path, monkeypatch):
        """When state is done, route to pre-merge review."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec")
        (tmp_path / "planning" / "hermes-plan-tdd-org.md").write_text("# Org Plan")
        (tmp_path / "planning" / "hermes-plan-tdd.md").write_text("# Approved Plan")

        state = SessionState(current_phase="done")
        state_path = tmp_path / ".hermes" / "session-state.json"
        save_state(state_path, state, expected_revision=0)

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Pre-Merge" in result, f"Expected pre-merge phase, got: {result}"
        assert "complete" in result.lower() or "review" in result.lower()

    def test_routes_to_plan_gate_when_approved_plan_without_org(self, tmp_path, monkeypatch):
        """When approved plan exists but org plan is missing, warn about bypass."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec Base")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# Refined Spec")
        # No hermes-plan-tdd-org.md
        (tmp_path / "planning" / "hermes-plan-tdd.md").write_text("# Approved Plan")

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Plan Gate" in result, f"Expected plan gate phase, got: {result}"
        assert "bypassed" in result.lower() or "missing" in result.lower()
