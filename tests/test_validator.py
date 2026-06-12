"""Tests for sbtdd_hermes.validator module."""

import pytest

from sbtdd_hermes.validator import (
    validate_update_field,
    validate_cross_fields,
    validate_full_update,
)
from sbtdd_hermes.state import SessionState


class TestValidateUpdateField:
    def test_valid_field(self):
        state = SessionState()
        ok, msg = validate_update_field("magi_iterations_used", 5, state)
        assert ok is True
        assert msg == ""

    def test_invalid_field_not_whitelisted(self):
        state = SessionState()
        ok, msg = validate_update_field("unknown_field", "value", state)
        assert ok is False
        assert "not whitelisted" in msg

    def test_type_mismatch(self):
        state = SessionState()
        ok, msg = validate_update_field("magi_iterations_used", "not_int", state)
        assert ok is False
        assert "Expected int" in msg

    def test_min_violation(self):
        state = SessionState()
        ok, msg = validate_update_field("magi_iterations_used", -1, state)
        assert ok is False
        assert "below minimum" in msg

    def test_max_violation(self):
        state = SessionState()
        ok, msg = validate_update_field("magi_iterations_used", 1000, state)
        assert ok is False
        assert "above maximum" in msg

    def test_invalid_phase_transition(self):
        state = SessionState(current_phase="red")
        ok, msg = validate_update_field("current_phase", "refactor", state)
        assert ok is False
        assert "Invalid transition" in msg

    def test_valid_phase_transition(self):
        state = SessionState(current_phase="red")
        ok, msg = validate_update_field("current_phase", "green", state)
        assert ok is True


class TestValidateCrossFields:
    def test_used_within_budget(self):
        state = SessionState(magi_iterations_used=3, magi_iteration_budget=5)
        ok, msg = validate_cross_fields(state)
        assert ok is True

    def test_used_exceeds_budget(self):
        state = SessionState(magi_iterations_used=5, magi_iteration_budget=3)
        ok, msg = validate_cross_fields(state)
        assert ok is False
        assert "exceeds budget" in msg

    def test_none_budget_passes(self):
        state = SessionState(magi_iterations_used=5, magi_iteration_budget=None)
        ok, msg = validate_cross_fields(state)
        assert ok is True


class TestValidateFullUpdate:
    def test_valid_full_update(self):
        state = SessionState(magi_iteration_budget=10)
        ok, msg = validate_full_update("magi_iterations_used", 5, state)
        assert ok is True

    def test_invalid_cross_field(self):
        state = SessionState(magi_iteration_budget=3)
        ok, msg = validate_full_update("magi_iterations_used", 5, state)
        assert ok is False
        assert "exceeds budget" in msg
