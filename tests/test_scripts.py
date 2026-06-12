"""Tests for sbtdd_hermes.scripts module."""

import json
from pathlib import Path

from sbtdd_hermes.scripts.verify import run_with_error_handling, run_verification
from sbtdd_hermes.scripts.git_status import check_git_status
from sbtdd_hermes.scripts.commit_helper import suggest_commit
from sbtdd_hermes.scripts.drift_check import check_drift


class TestVerify:
    def test_run_with_error_handling_success(self):
        ok, output = run_with_error_handling(["python", "--version"])
        assert ok is True
        assert "Python" in output

    def test_run_with_error_handling_missing_tool(self):
        ok, output = run_with_error_handling(["nonexistent_tool_12345"])
        assert ok is False
        assert "not found" in output.lower() or "error" in output.lower()

    def test_run_verification_check_only(self):
        result = run_verification("python", check_only=True)
        assert result["stack"] == "python"
        assert "results" in result

    def test_run_verification_default(self):
        result = run_verification("python")
        assert result["stack"] == "python"
        # May pass or fail depending on environment
        assert "all_passed" in result


class TestGitStatus:
    def test_check_git_status(self):
        # Only works in git repo
        result = check_git_status()
        assert "has_changes" in result
        assert "last_commit_message" in result or result["last_commit_message"] is None


class TestCommitHelper:
    def test_suggest_commit_red(self):
        msg = suggest_commit("red", "parser edge cases")
        assert msg.startswith("test:")
        assert "parser edge cases" in msg

    def test_suggest_commit_green(self):
        msg = suggest_commit("green", "parser edge cases")
        assert msg.startswith("feat:")

    def test_suggest_commit_refactor(self):
        msg = suggest_commit("refactor", "parser")
        assert msg.startswith("refactor:")


class TestDriftCheck:
    def test_no_state_file(self, tmp_path):
        result = check_drift(tmp_path / "nonexistent.json")
        assert result["classification"] == "N/A"

    def test_consistent_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"current_phase": "red"}))
        # Without git repo, last_prefix will be None
        result = check_drift(state_path)
        assert result["classification"] in ["N/A", "UNRECOGNISED", "CONSISTENT"]
