import dataclasses
from typing import Callable

from ._config import (
    PHASE_TRANSITIONS,
    STATE_UPDATE_FIELDS,
    CROSS_FIELD_VALIDATORS,
)
from .state import SessionState


def validate_update_field(field: str, value, current_state: SessionState) -> tuple[bool, str]:
    if field not in STATE_UPDATE_FIELDS:
        return False, f"Field '{field}' not whitelisted"

    spec = STATE_UPDATE_FIELDS[field]

    if not isinstance(value, spec["type"]):
        return False, f"Expected {spec['type'].__name__}, got {type(value).__name__}"

    if "min" in spec and value < spec["min"]:
        return False, f"Value below minimum {spec['min']}"
    if "max" in spec and value > spec["max"]:
        return False, f"Value above maximum {spec['max']}"

    if "choices" in spec and value not in spec["choices"]:
        return False, f"Value not in allowed choices"

    if spec.get("validate") == "phase_transition":
        old = current_state.current_phase
        if value not in PHASE_TRANSITIONS.get(old, set()):
            allowed = PHASE_TRANSITIONS.get(old, set())
            return False, f"Invalid transition: {old} -> {value}. Allowed: {allowed}"

    if "max_length" in spec and len(value) > spec["max_length"]:
        return False, f"String exceeds max length"

    return True, ""


def validate_cross_fields(new_state: SessionState) -> tuple[bool, str]:
    for field_a, field_b, check, template in CROSS_FIELD_VALIDATORS:
        val_a = getattr(new_state, field_a)
        val_b = getattr(new_state, field_b)
        if not check(val_a, val_b):
            return False, template.format(u=val_a, b=val_b, v=val_a, c=val_b)
    return True, ""


def validate_full_update(field: str, value, current_state: SessionState) -> tuple[bool, str]:
    ok, msg = validate_update_field(field, value, current_state)
    if not ok:
        return False, msg

    new_state = dataclasses.replace(current_state, **{field: value})
    return validate_cross_fields(new_state)
