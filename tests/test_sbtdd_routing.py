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
        """When spec-behavior-base.md has template markers, route to specification_edit."""
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
        assert "Specification (Edit)" in result, f"Expected specification_edit phase, got: {result}"
        assert "template markers" in result.lower() or "fill it in" in result.lower()

    def test_routes_to_brainstorm_when_spec_behavior_missing(self, tmp_path, monkeypatch):
        """When spec-behavior-base.md is filled but spec-behavior.md missing, route to brainstorm."""
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
        assert "Specification (Brainstorm)" in result, f"Expected specification_brainstorm phase, got: {result}"
        assert "spec-behavior-base.md" in result.lower()
        assert "MyFeature" in result  # content is embedded in prompt
        assert "appropriate file-writing tool" in result.lower()

    def test_brainstorm_escapes_backticks_in_spec_base(self, tmp_path, monkeypatch):
        """Triple backticks in spec-base must not break the outer markdown block."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # spec with triple backticks inside
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n```python\nprint('hello')\n```\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Outer fence uses 4 backticks (3+1); inner 3-backtick blocks are safe
        assert "````markdown" in result
        assert "print('hello')" in result
        assert "````" in result

    def test_brainstorm_handles_four_backticks_in_spec(self, tmp_path, monkeypatch):
        """Four backticks in spec-base must not break the outer fence."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # spec with four backticks inside — fence must adapt to 5 backticks
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n````python\nprint('hello')\n````\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Outer fence must be 5 backticks (4+1)
        assert "`````markdown" in result
        assert "print('hello')" in result
        assert "`````" in result

    def test_brainstorm_handles_many_backticks_in_spec(self, tmp_path, monkeypatch):
        """Many consecutive backticks in spec-base must not break the outer fence."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # spec with 25 backticks inside — fence must adapt to 26 backticks
        backticks = "`" * 25
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            f"# Spec\n\n{backticks}python\nprint('hello')\n{backticks}\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Outer fence must be 26 backticks (25+1)
        fence = "`" * 26
        assert f"{fence}markdown" in result
        assert "print('hello')" in result
        assert fence in result

    def test_brainstorm_uses_unbounded_fence_for_extreme_backticks(self, tmp_path, monkeypatch):
        """Many consecutive backticks >64 should still produce a safe fence."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # spec with 65 backticks inside — fence must grow to 66 backticks
        backticks = "`" * 65
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            f"# Spec\n\n{backticks}python\nprint('hello')\n{backticks}\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Fence must be 66 backticks (65+1) to stay safe
        fence = "`" * 66
        assert f"{fence}markdown" in result
        assert "print('hello')" in result
        assert fence in result

    def test_brainstorm_fence_increments_on_indented_closer(self, tmp_path, monkeypatch):
        """If content contains a line that could close the fence, fence must grow."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Content with a line of 4 backticks — this would close a fence of 4 backticks,
        # so the fence must grow to 5 backticks to remain safe.
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n````\nprint('hello')\n````\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Content has 4 backticks in a line, so fence must be at least 5
        assert "`````markdown" in result
        assert "print('hello')" in result
        assert "`````" in result

    def test_brainstorm_fence_increments_on_indented_with_spaces(self, tmp_path, monkeypatch):
        """CommonMark allows up to 3 spaces before a closing fence."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Content with a line "   ````" (3 spaces + 4 backticks) — per CommonMark this
        # would close a fence of 4 backticks, so fence must grow to 5.
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n   ````\nprint('hello')\n   ````\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # 3 spaces + 4 backticks would close a 4-backtick fence, so must use 5
        assert "`````markdown" in result
        assert "print('hello')" in result
        assert "`````" in result

    def test_brainstorm_fence_increments_with_tabs(self, tmp_path, monkeypatch):
        """CommonMark allows tabs after a closing fence."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Content with a line "````\t" (4 backticks + tab) — per CommonMark this
        # would close a fence of 4 backticks, so fence must grow to 5.
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n````\t\nprint('hello')\n````\t\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # 4 backticks + tab would close a 4-backtick fence, so must use 5
        assert "`````markdown" in result
        assert "print('hello')" in result
        assert "`````" in result

    def test_brainstorm_fence_detects_more_backticks_than_max_run(self, tmp_path, monkeypatch):
        """A line with N+1 backticks must be detected even if max run is N.

        This tests the corrected regex in _is_fence_safe: it must match lines
        with AT LEAST fence_len backticks, not exactly fence_len.
        """
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Content: max consecutive backticks is 4 (from the first block),
        # but there's also a line with 5 backticks that would close a fence of 4.
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n````\nprint('hello')\n````\n\n`````\nextra\n`````\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Max run is 5, so fence must be at least 6. But also, a line with 5
        # backticks would close a fence of 5, so fence must be 6.
        assert "``````markdown" in result
        assert "print('hello')" in result
        assert "``````" in result

    def test_brainstorm_fence_detects_exact_backtick_boundary(self, tmp_path, monkeypatch):
        """A line with EXACTLY fence_len backticks must force increment.

        If content has a line with 4 backticks, a fence of 4 backticks is unsafe,
        so the fence must grow to 5.
        """
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # No triple backticks in content, but there IS a line with exactly 4 backticks
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(
            "# Spec\n\n````\nprint('hello')\n````\n\n**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Content has a line with 4 backticks, so fence must be at least 5
        assert "`````markdown" in result
        assert "print('hello')" in result
        assert "`````" in result

    def test_brainstorm_empty_spec_base(self, tmp_path, monkeypatch):
        """Empty spec-base should still produce a valid brainstorm prompt."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Empty spec base
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("")

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        # Fence should be minimum 4 backticks
        assert "````markdown" in result

    def test_brainstorm_non_utf8_content(self, tmp_path, monkeypatch):
        """Non-UTF8 bytes in spec-base are treated as incomplete (specification_edit)."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Write invalid UTF-8 bytes
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_bytes(
            b"# Spec\n\n\xff\xfe**Feature:** X"
        )

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        # Non-UTF8 file is treated as incomplete (can't verify markers)
        assert "Specification (Edit)" in result
        assert "fill it in" in result.lower() or "template markers" in result.lower()

    def test_brainstorm_oserror_returns_error(self, tmp_path, monkeypatch):
        """OSError during read should return a user-friendly error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Create spec base
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text("# Spec")

        # Patch Path.open to raise PermissionError on the spec file ONLY in binary mode
        # (build_brainstorm_prompt uses open("rb"); _has_template_markers uses read_text)
        from pathlib import Path as _Path
        real_path_open = _Path.open

        def fake_path_open(self, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "r")
            if self.name == "spec-behavior-base.md" and mode == "rb":
                raise PermissionError("Permission denied")
            return real_path_open(self, *args, **kwargs)

        monkeypatch.setattr(_Path, "open", fake_path_open)

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Error" in result or "Permission denied" in result or "reading" in result.lower()

    def test_brainstorm_exact_max_bytes_no_truncation(self, tmp_path, monkeypatch):
        """Spec-base exactly MAX_BYTES must NOT show truncation notice."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # 100,000 'A' chars = exactly MAX_BYTES in UTF-8
        exact_content = "A" * 100_000
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(exact_content)

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        assert "truncated" not in result.lower()
        assert "exceeds safe size" not in result.lower()

    def test_brainstorm_truncates_oversized_spec(self, tmp_path, monkeypatch):
        """Spec-base > 100KB must be truncated with a notice showing actual file size."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Create a 110KB spec base
        large_content = "A" * 110_000
        (tmp_path / "sbtdd" / "spec-behavior-base.md").write_text(large_content)

        ctx = MagicMock()
        register(ctx)
        handler = self._get_handler(ctx)

        result = handler("")
        assert "Specification (Brainstorm)" in result
        assert "truncated" in result.lower() or "exceeds safe size" in result.lower()
        # The notice should report the ACTUAL file size (110000), not the read size (100001)
        assert "110000" in result

    def test_brainstorm_missing_spec_base_returns_error(self, tmp_path, monkeypatch):
        """If spec-behavior-base.md vanishes between phase check and prompt build, return error."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "sbtdd").mkdir()
        (tmp_path / "planning").mkdir()
        (tmp_path / ".hermes").mkdir()

        # Phase detection requires file to exist... this is a synthetic test
        # We directly test build_brainstorm_prompt with a non-existent path
        from sbtdd_hermes.prompts import build_brainstorm_prompt
        result = build_brainstorm_prompt(tmp_path)
        assert "Error" in result or "not found" in result.lower()

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
