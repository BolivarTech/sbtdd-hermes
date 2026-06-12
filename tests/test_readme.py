"""
TDD: README v2.0.0 plugin documentation.

This test MUST fail before implementation (RED phase).
"""

import pytest
from pathlib import Path


README_PATH = Path(__file__).parent.parent / "README.md"


class TestReadmeV200:
    """RED: README must document plugin v2.0.0 features."""

    def test_readme_exists(self):
        assert README_PATH.exists(), "README.md not found at project root"

    def test_readme_mentions_plugin_not_skill(self):
        content = README_PATH.read_text(encoding="utf-8")
        # Should say "plugin" not "skill"
        assert "plugin" in content.lower(), "README should mention plugin"
        # Should NOT say "skill" as primary term
        skill_count = content.lower().count("skill")
        plugin_count = content.lower().count("plugin")
        assert plugin_count >= skill_count, \
            f"README should emphasize plugin ({plugin_count}) over skill ({skill_count})"

    def test_readme_documents_commands(self):
        content = README_PATH.read_text(encoding="utf-8")
        commands = ["/sbtdd", "/sbtdd-init", "/sbtdd-check", "/sbtdd-override"]
        for cmd in commands:
            assert cmd in content, f"README should document command {cmd}"

    def test_readme_documents_tools(self):
        content = README_PATH.read_text(encoding="utf-8")
        tools = ["sbtdd_status", "sbtdd_update_state"]
        for tool in tools:
            assert tool in content, f"README should document tool {tool}"

    def test_readme_has_installation_section(self):
        content = README_PATH.read_text(encoding="utf-8")
        assert "install" in content.lower(), "README should have installation instructions"
        assert "hermes" in content.lower(), "README should mention Hermes Agent"
        assert "entry-point" in content.lower() or "entry_point" in content.lower(), \
            "README should mention entry-point registration"

    def test_readme_has_version_200(self):
        content = README_PATH.read_text(encoding="utf-8")
        assert "2.0.0" in content, "README should mention version 2.0.0"

    def test_readme_documents_hooks(self):
        content = README_PATH.read_text(encoding="utf-8")
        assert "pre_tool_call" in content, "README should document pre_tool_call hook"
        assert "TDD-Guard" in content, "README should document TDD-Guard"
