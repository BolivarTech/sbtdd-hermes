"""Tests for sbtdd_hermes.state module."""

import json
import pytest
from pathlib import Path
from dataclasses import dataclass

from sbtdd_hermes.state import (
    SessionState,
    load_state,
    save_state,
    migrate_state,
    ConcurrencyError,
    SaveError,
    MigrationError,
)


class TestSessionState:
    def test_default_values(self):
        s = SessionState()
        assert s.schema_version == 1
        assert s.state_revision == 0
        assert s.current_phase == "red"
        assert s.current_task_id is None

    def test_to_dict(self):
        s = SessionState(current_phase="green")
        d = s.to_dict()
        assert d["current_phase"] == "green"
        assert d["schema_version"] == 1

    def test_from_dict(self):
        d = {"schema_version": 1, "state_revision": 5, "current_phase": "refactor",
             "plan_path": "plan.md", "current_task_id": None, "current_task_title": None,
             "phase_started_at_commit": "", "last_verification_at": None,
             "last_verification_result": None, "magi_iteration_budget": None,
             "magi_iterations_used": 0, "magi_target_verdict": None,
             "tdd_guard_override": {}, "tdd_guard_override_count": 0,
             "last_override_reason": "", "notes": ""}
        s = SessionState.from_dict(d)
        assert s.state_revision == 5
        assert s.current_phase == "refactor"


class TestLoadState:
    def test_missing_file_returns_default(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        state = load_state(path)
        assert state.state_revision == 0
        assert state.current_phase == "red"

    def test_load_valid_state(self, tmp_path):
        path = tmp_path / "state.json"
        data = {"schema_version": 1, "state_revision": 3, "current_phase": "green",
                "plan_path": "plan.md", "current_task_id": "t1", "current_task_title": "Task 1",
                "phase_started_at_commit": "", "last_verification_at": None,
                "last_verification_result": None, "magi_iteration_budget": None,
                "magi_iterations_used": 0, "magi_target_verdict": None,
                "tdd_guard_override": {}, "tdd_guard_override_count": 0,
                "last_override_reason": "", "notes": ""}
        path.write_text(json.dumps(data))
        state = load_state(path)
        assert state.state_revision == 3
        assert state.current_phase == "green"

    def test_load_corrupted_file_returns_default(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("not json")
        state = load_state(path)
        assert state.state_revision == 0

    def test_migrate_old_file(self, tmp_path):
        path = tmp_path / "state.json"
        data = {"schema_version": 1, "current_phase": "red"}  # Missing state_revision
        path.write_text(json.dumps(data))
        state = load_state(path)
        assert state.state_revision == 0
        assert state.schema_version == 1


class TestSaveState:
    def test_save_new_state(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState(current_phase="green")
        save_state(path, state, expected_revision=0)
        assert path.exists()
        loaded = load_state(path)
        assert loaded.current_phase == "green"
        assert loaded.state_revision == 1  # Incremented

    def test_concurrency_error_on_mismatch(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState()
        save_state(path, state, expected_revision=0)
        
        with pytest.raises(ConcurrencyError):
            save_state(path, state, expected_revision=0)  # stale revision

    def test_save_increments_revision(self, tmp_path):
        path = tmp_path / "state.json"
        state = SessionState()
        save_state(path, state, expected_revision=0)
        assert state.state_revision == 1
        
        save_state(path, state, expected_revision=1)
        assert state.state_revision == 2

    def test_creates_directory(self, tmp_path):
        path = tmp_path / "subdir" / "state.json"
        state = SessionState()
        save_state(path, state, expected_revision=0)
        assert path.exists()


class TestMigrateState:
    def test_version_1_migration(self):
        data = {"schema_version": 1, "current_phase": "red"}
        state = migrate_state(data)
        assert state.schema_version == 1
        assert state.state_revision == 0

    def test_unsupported_version_raises(self):
        data = {"schema_version": 999}
        with pytest.raises(MigrationError):
            migrate_state(data)
