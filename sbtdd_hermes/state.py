import json
import os
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path

import filelock

from ._config import (
    STATE_SCHEMA_VERSION,
    FILELOCK_RETRY_ATTEMPTS,
    FILELOCK_RETRY_DELAYS,
    STRICT_MODE,
)


class ConcurrencyError(RuntimeError):
    pass


class SaveError(RuntimeError):
    pass


class MigrationError(RuntimeError):
    pass


@dataclass
class SessionState:
    schema_version: int = 1
    state_revision: int = 0
    plan_path: str = "planning/hermes-plan-tdd.md"
    current_task_id: str | None = None
    current_task_title: str | None = None
    current_phase: str = "red"
    phase_started_at_commit: str = ""
    last_verification_at: str | None = None
    last_verification_result: str | None = None
    magi_iteration_budget: int | None = None
    magi_iterations_used: int = 0
    magi_backend: str = "ollama"
    magi_target_verdict: str | None = None
    tdd_guard_override: dict = field(default_factory=dict)
    tdd_guard_override_count: int = 0
    last_override_reason: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        return cls(**data)


def load_state(path: Path) -> SessionState:
    if not path.exists():
        return SessionState()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        if STRICT_MODE:
            raise
        warnings.warn(f"Corrupted state file at {path}: {e}. Starting fresh.")
        return SessionState()

    if data.get("schema_version", 1) != STATE_SCHEMA_VERSION:
        try:
            migrated = migrate_state(data)
            _persist_migrated(path, migrated)
            return migrated
        except MigrationError as e:
            if STRICT_MODE:
                raise
            warnings.warn(f"Migration failed for {path}: {e}. Starting fresh.")
            return SessionState()

    if "state_revision" not in data:
        data["state_revision"] = 0

    return SessionState(**data)


def _persist_migrated(path: Path, state: SessionState) -> None:
    data = state.to_dict()
    data["state_revision"] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(str(temp), str(path))


def save_state(path: Path, state: SessionState, expected_revision: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    for attempt, delay in enumerate(FILELOCK_RETRY_DELAYS):
        try:
            with filelock.FileLock(str(path) + ".lock", timeout=5):
                current = load_state(path)
                if current.state_revision != expected_revision:
                    raise ConcurrencyError(
                        f"Expected revision {expected_revision}, found {current.state_revision}. "
                        f"Another process modified the state. Reload and retry."
                    )

                data = state.to_dict()
                data["state_revision"] = data.get("state_revision", 0) + 1

                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                os.replace(str(temp), str(path))

                state.state_revision = data["state_revision"]
                return

        except ConcurrencyError:
            raise
        except Exception as e:
            if attempt < len(FILELOCK_RETRY_DELAYS) - 1:
                import time
                time.sleep(delay)
            else:
                raise SaveError(
                    f"Failed to save state after {FILELOCK_RETRY_ATTEMPTS} attempts: {e}"
                ) from e


def migrate_state(data: dict) -> SessionState:
    old_version = data.get("schema_version", 1)

    if old_version == 1:
        if "state_revision" not in data:
            data["state_revision"] = 0
        data["schema_version"] = STATE_SCHEMA_VERSION
        return SessionState(**data)

    raise MigrationError(f"Unsupported schema version: {old_version}")
