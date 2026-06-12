"""Tests for sbtdd_hermes._config module."""

from sbtdd_hermes._config import (
    TDDGUARD_TOOL_NAMES,
    PHASE_TRANSITIONS,
    STATE_UPDATE_FIELDS,
    CROSS_FIELD_VALIDATORS,
)


def test_tddguard_tool_names():
    assert "write_file" in TDDGUARD_TOOL_NAMES
    assert "patch" in TDDGUARD_TOOL_NAMES


def test_phase_transitions():
    assert "green" in PHASE_TRANSITIONS["red"]
    assert "done" in PHASE_TRANSITIONS["red"]
    assert "refactor" in PHASE_TRANSITIONS["green"]
    assert PHASE_TRANSITIONS["done"] == set()


def test_state_update_fields():
    assert "magi_iterations_used" in STATE_UPDATE_FIELDS
    assert "current_phase" in STATE_UPDATE_FIELDS
    assert "magi_target_verdict" in STATE_UPDATE_FIELDS


def test_cross_field_validators():
    assert len(CROSS_FIELD_VALIDATORS) >= 1
    # First validator should be used <= budget
    field_a, field_b, check, template = CROSS_FIELD_VALIDATORS[0]
    assert field_a == "magi_iterations_used"
    assert field_b == "magi_iteration_budget"
    assert check(3, 5) is True
    assert check(5, 3) is False
