import json
import os
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ._config import (
    STATE_SCHEMA_VERSION,
    FILELOCK_RETRY_ATTEMPTS,
    FILELOCK_RETRY_DELAYS,
    STRICT_MODE,
)

# Optional filelock — Hermes stripped venv may not have it
try:
    import filelock
    _HAS_FILELOCK = True
except ImportError:
    _HAS_FILELOCK = False


class _FallbackFileLock:
    """Cross-platform file lock fallback when filelock is unavailable."""
    def __init__(self, lock_path: str) -> None:
        self.lock_path = Path(lock_path)

    def acquire(self, timeout: float = -1) -> None:
        import time
        start = time.time()
        while True:
            try:
                # Exclusive creation — fails if lock exists
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return
            except FileExistsError:
                if timeout > 0 and time.time() - start > timeout:
                    raise TimeoutError(f"Could not acquire lock {self.lock_path}")
                time.sleep(0.05)

    def release(self) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self) -> "_FallbackFileLock":
        self.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()


def _get_lock(lock_path: str) -> Any:
    """Return a file lock context manager (filelock or fallback)."""
    if _HAS_FILELOCK:
        return filelock.FileLock(lock_path, timeout=5)
    return _FallbackFileLock(lock_path)


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
    stack: str | None = None
    tdd_guard_override: dict[str, Any] = field(default_factory=dict)
    tdd_guard_override_count: int = 0
    last_override_reason: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
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
            with _get_lock(str(path) + ".lock"):
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


def migrate_state(data: dict[str, Any]) -> SessionState:
    """Forward-only migration: upgrades old schema versions to current.

    NOTE: This migration is forward-only. Downgrading the plugin after
    state migration may leave the state file unreadable by older versions.
    Re-installing an older plugin requires manual state reset or re-init.
    """
    old_version = data.get("schema_version", 1)

    if old_version == 1:
        if "state_revision" not in data:
            data["state_revision"] = 0
        data["schema_version"] = STATE_SCHEMA_VERSION
        return SessionState(**data)

    raise MigrationError(f"Unsupported schema version: {old_version}")
