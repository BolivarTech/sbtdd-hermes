# SBTDD-Hermes Plugin — Plan de Implementacion FINAL (Opcion C: Hibrido)

> **Arquitectura:** Plugin nativo Hermes (estado + orquestacion + TDD-Guard hook) + Scripts auxiliares Python + Referencias instructivas.
> **MAGI Rounds 1-5:** TODOS los findings han sido incorporados.
> **Veredicto MAGI:** GO WITH CAVEATS (aceptado). 5 rounds, 50+ findings resueltos.
> **Estado:** IMPLEMENTANDO. Task 1 en progreso.

---

## 0. Resumen de Fixes MAGI (5 Rounds = 50+ findings)

### Rounds 1-3 — 30 findings (CORREGIDOS en v7)
- Tool `sbtdd_update_state` agregado
- Atomic write via `tempfile` + `os.replace()`
- MAGI parser con version detection + fallback `HOLD`
- `schema_version` + `state_revision` separados
- `expected_revision` obligatorio
- State machine `PHASE_TRANSITIONS`
- `override_count` + auditoria
- Regex lineales O(n) + timeout via `multiprocessing.Process`
- Cross-field validation

### Round 4 — 15 findings (CORREGIDOS en v9)
- Funciones top-level picklables (`_do_parse`, `_queue_wrapper`)
- `state_revision` incrementa en dict antes de serializar
- `queue.get(timeout=1.0)`
- `migrate_state()` agrega `state_revision=0`
- Windows compat via spawn
- Cache usa `st_mtime_ns`
- Override scoped por `tool` + `path`
- `MigrationError` capturada en `load_state()`
- Single state file documentado como limitacion

### Round 5 — 8 micro-fixes (CORREGIDOS EN ESTA VERSION)

| Finding MAGI | Severidad | Fix |
|---|---|---|
| OCC revision check fuera de filelock | **CRITICAL** | `save_state()` carga state + valida `expected_revision` **dentro** del `with filelock` block. Read-check-write atomico. |
| Migrated state no persiste | WARNING | `load_state()` persiste estado migrado inmediatamente via `save_state(path, migrated, expected_revision=migrated.state_revision)`. |
| Directorio `.hermes/` no existe | WARNING | `save_state()` crea directorio con `path.parent.mkdir(parents=True, exist_ok=True)` antes de escribir. |
| Filelock timeout sin retry | WARNING | `save_state()` reintenta con backoff: 3 intentos, delays 0.1s, 0.5s, 1.0s. |
| Cache TOCTOU en multi-proceso | INFO | Documentado: "single Hermes session per project directory". Cache no necesita lock en este modelo. |
| Override one-shot consumption risk | INFO | Documentado en `references/tdd-cycle.md`: "override se consume al permitir el tool call. Si el tool falla posteriormente, el usuario debe re-solicitar override." |
| Resilient error handling puede enmascarar bugs | INFO | `_config.py`: `STRICT_MODE = os.environ.get("SBTDD_STRICT", "false").lower() == "true"`. En strict mode, `load_state()` falla en vez de retornar default. |
| Windows spawn requiere imports limpios | INFO | `magi_parser.py`: no side effects en import time. Verificado. |

---

## 1. Estructura del Paquete (FINAL)

```
sbtdd-hermes-plugin/
├── pyproject.toml                    # Entry-point: hermes_agent.plugins
├── plugin.yaml                       # Metadata del plugin
├── sbtdd_hermes/
│   ├── __init__.py                   # register(ctx) + hooks + state cache
│   ├── commands.py                   # Handlers /sbtdd, /sbtdd-init, /sbtdd-check
│   ├── state.py                      # SessionState v1 + state_revision + OCC + filelock + migrate
│   ├── validator.py                  # Validacion de commits + checklist + update validation
│   ├── prompts.py                    # Generadores de prompts/instrucciones
│   ├── scaffolding.py                # Init logic (stack detection, template rendering)
│   ├── magi_parser.py                # Parser MAGI con regex seguras + multiprocessing timeout
│   ├── _config.py                  # Constantes + state machine + regex audit
│   └── scripts/
│       ├── __init__.py               # Re-export para import directo
│       ├── verify.py               # Ejecuta verificacion §0.1 por stack
│       ├── git_status.py           # Ejecuta git status + git log
│       ├── drift_check.py          # Detecta drift entre state y git log
│       └── commit_helper.py      # Genera mensajes de commit sugeridos
├── templates/
│   ├── HERMES.local.md.tmpl        # ~200 lineas (esencial: §0, §1, §2, §4, §5)
│   ├── spec-behavior-base.tmpl.md  # Seed de spec
│   └── verification/
│       ├── rust.md                   # Comandos §0.1 Rust
│       ├── python.md                 # Comandos §0.1 Python
│       └── cpp.md                    # Comandos §0.1 C/C++
├── references/
│   ├── routing.md                    # Phase detection + artifact map
│   ├── review-gates.md             # Gate criteria + MAGI integration
│   ├── tdd-cycle.md                # TDD procedure + TDD-Guard behavior
│   ├── finalization.md             # Checklist §7
│   └── port-claude-to-hermes.md     # Migration notes + Hermes API dependencies
└── tests/
    ├── test_plugin.py
    ├── test_state.py                 # Tests de migracion + OCC + filelock
    ├── test_validator.py
    ├── test_magi_parser.py           # Tests de ReDoS + timeout
    ├── test_scripts.py
    ├── test_config.py
    └── test_concurrency.py           # Tests de OCC + concurrent updates
```

---

## 2. Plugin Nativo (Especificacion Completa para Implementacion)

### 2.1 `_config.py`

```python
import os

# === TDD-Guard ===
TDDGUARD_TOOL_NAMES = {"write_file", "patch", "terminal"}
TDDGUARD_TEST_PATTERNS = [
    r"tests?/",
    r"test_[^/]+\.py$",
    r"[^/]+_test\.py$",
]
TDDGUARD_CONFIDENCE_THRESHOLD = 0.7
MAX_OVERRIDE_PER_SESSION = 3

# === Timeouts ===
SCRIPT_TIMEOUT = 60
MAGI_PARSE_TIMEOUT = 5.0

# === State ===
STATE_SCHEMA_VERSION = 1

# === MAGI Parser ===
MAGI_SUPPORTED_FORMATS = ["2.0"]
MAGI_BANNER_RE = r"\+={52}\+"
MAGI_VEREDICTO_RE = r"\|\s+CONSENSUS:\s+([^|]+)\s+\|"
MAGI_FINDING_RE = r"\[([!]+)\]\s+\[(\w+)\]\s+([^\n]*)"

# === Phase State Machine ===
PHASE_TRANSITIONS = {
    "red": {"green", "done"},       # done = abort
    "green": {"refactor", "done"},
    "refactor": {"red", "done"},     # red = next task
    "done": set(),
}
VALID_PHASES = set(PHASE_TRANSITIONS.keys())

# === Update Whitelist (agente puede mutar) ===
STATE_UPDATE_FIELDS = {
    "magi_iterations_used": {"type": int, "min": 0, "max": 999},
    "magi_iteration_budget": {"type": int, "min": 1, "max": 99},
    "magi_target_verdict": {
        "type": str,
        "choices": {
            "STRONG GO", "GO", "GO WITH CAVEATS",
            "HOLD", "HOLD -- TIE", "STRONG NO-GO"
        }
    },
    "current_phase": {"type": str, "validate": "phase_transition"},
    "notes": {"type": str, "max_length": 1000},
}

# === Cross-field Validators ===
CROSS_FIELD_VALIDATORS = [
    ("magi_iterations_used", "magi_iteration_budget",
     lambda u, b: b is None or u <= b,
     "magi_iterations_used ({u}) exceeds budget ({b})"),
    ("last_verification_at", "phase_started_at_commit",
     lambda v, c: c == "" or v is None or v >= c,
     "last_verification_at ({v}) before phase_started_at_commit ({c})"),
]

# === Strict Mode ===
STRICT_MODE = os.environ.get("SBTDD_STRICT", "false").lower() == "true"

# === Retry Config ===
FILELOCK_RETRY_ATTEMPTS = 3
FILELOCK_RETRY_DELAYS = [0.1, 0.5, 1.0]  # segundos
```

### 2.2 `state.py`

```python
import json
import os
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import filelock

from ._config import STATE_SCHEMA_VERSION, FILELOCK_RETRY_ATTEMPTS, FILELOCK_RETRY_DELAYS, STRICT_MODE


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
    """Lee estado. Fallback a default si corrupto, no existe, o migracion falla."""
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

    # Migracion si es necesario
    if data.get("schema_version", 1) != STATE_SCHEMA_VERSION:
        try:
            migrated = migrate_state(data)
            # Persistir estado migrado inmediatamente
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
    """Persiste estado migrado sin OCC (primera vez)."""
    data = state.to_dict()
    data["state_revision"] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(str(temp), str(path))


def save_state(path: Path, state: SessionState, expected_revision: int) -> None:
    """
    Guarda estado con OCC + filelock + retry.
    Read-check-write atomico dentro del lock.
    """
    # Asegurar directorio existe
    path.parent.mkdir(parents=True, exist_ok=True)

    # Retry loop
    for attempt, delay in enumerate(FILELOCK_RETRY_DELAYS):
        try:
            with filelock.FileLock(str(path) + ".lock", timeout=5):
                # Read + check DENTRO del lock (FIX round 5)
                current = load_state(path)
                if current.state_revision != expected_revision:
                    raise ConcurrencyError(
                        f"Expected revision {expected_revision}, found {current.state_revision}. "
                        f"Another process modified the state. Reload and retry."
                    )

                # Preparar datos con revision incrementada
                data = state.to_dict()
                data["state_revision"] = data.get("state_revision", 0) + 1

                # Write atomico
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                os.replace(str(temp), str(path))

                # Sincronizar objeto en memoria
                state.state_revision = data["state_revision"]
                return  # exito

        except ConcurrencyError:
            raise  # no reintentar conflictos de concurrencia
        except Exception as e:
            if attempt < len(FILELOCK_RETRY_DELAYS) - 1:
                import time
                time.sleep(delay)
            else:
                raise SaveError(f"Failed to save state after {FILELOCK_RETRY_ATTEMPTS} attempts: {e}") from e


def migrate_state(data: dict) -> SessionState:
    """Migra estado antiguo a schema actual."""
    old_version = data.get("schema_version", 1)

    if old_version == 1:
        if "state_revision" not in data:
            data["state_revision"] = 0
        data["schema_version"] = STATE_SCHEMA_VERSION
        return SessionState(**data)

    raise MigrationError(f"Unsupported schema version: {old_version}")
```

### 2.3 `magi_parser.py`

```python
import multiprocessing
import re
from typing import Callable

from ._config import MAGI_PARSE_TIMEOUT, MAGI_BANNER_RE, MAGI_VEREDICTO_RE, MAGI_FINDING_RE


class ParseError(RuntimeError):
    pass


# === Funciones top-level (picklables) ===

def _do_parse(report: str) -> dict:
    """Parsea reporte MAGI. Top-level para compatibilidad con multiprocessing."""
    if "+==================================================+" not in report:
        raise ParseError("Missing MAGI banner")
    if "CONSENSUS:" not in report:
        raise ParseError("Missing consensus section")

    verdict_match = re.search(MAGI_VEREDICTO_RE, report)
    if not verdict_match:
        raise ParseError("Could not extract verdict")

    findings = []
    for line in report.splitlines():
        m = re.match(MAGI_FINDING_RE, line)
        if m:
            findings.append({"severity": m.group(2), "title": m.group(3)})

    return {
        "veredicto": verdict_match.group(1).strip(),
        "findings": findings,
        "format_version": "2.0",
        "parse_confidence": 1.0 if findings else 0.5,
    }


def _queue_wrapper(queue, func, args):
    """Wrapper top-level para multiprocessing.Process."""
    try:
        result = func(*args)
        queue.put(("ok", result))
    except Exception as e:
        queue.put(("error", e))


def run_with_regex_timeout(func: Callable, func_args: tuple, timeout: float = MAGI_PARSE_TIMEOUT):
    """Ejecuta funcion con timeout via multiprocessing.Process."""
    result_queue = multiprocessing.Queue()

    p = multiprocessing.Process(target=_queue_wrapper, args=(result_queue, func, func_args))
    p.start()
    p.join(timeout=timeout)

    if p.is_alive():
        p.terminate()
        p.join(timeout=1.0)
        raise TimeoutError(f"MAGI parsing exceeded {timeout}s")

    try:
        status, payload = result_queue.get(timeout=1.0)
    except Exception:
        raise ParseError("MAGI parsing failed: worker terminated before producing result")

    if status == "error":
        raise payload
    return payload


def parse_magi_report(report: str) -> dict:
    """Parsea reporte MAGI con timeout enforceable."""
    try:
        return run_with_regex_timeout(_do_parse, (report,), timeout=MAGI_PARSE_TIMEOUT)
    except TimeoutError:
        raise ParseError("MAGI parsing timeout")
```

### 2.4 `validator.py`

```python
import dataclasses
from typing import Callable

from ._config import (
    COMMIT_PREFIXES, COMMIT_MESSAGE_RULES, MAGI_VERDICTS,
    STATE_UPDATE_FIELDS, PHASE_TRANSITIONS, CROSS_FIELD_VALIDATORS,
)
from .state import SessionState


def validate_commit_prefix(message: str, phase: str) -> tuple[bool, str]:
    """Verifica que el prefijo del commit corresponda a la fase."""
    # ... implementacion ...
    pass


def validate_commit_message(message: str) -> tuple[bool, list[str]]:
    """Verifica reglas de mensaje (ingles, <=72, sin IA, sin Co-Authored-By)."""
    # ... implementacion ...
    pass


def validate_commit_atomicity(diff: str) -> tuple[bool, str]:
    """Verifica que el commit sea atomico (single-purpose)."""
    # ... implementacion ...
    pass


def is_commit_authorized_under_plan(message: str, state: SessionState) -> bool:
    """Verifica si el commit esta autorizado bajo plan aprobado."""
    # ... implementacion ...
    pass


def validate_update_field(field: str, value, current_state: SessionState) -> tuple[bool, str]:
    """Valida tipo, rango, choices, transiciones de fase."""
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
    """Valida consistencia entre campos relacionados."""
    for field_a, field_b, check, template in CROSS_FIELD_VALIDATORS:
        val_a = getattr(new_state, field_a)
        val_b = getattr(new_state, field_b)
        if not check(val_a, val_b):
            return False, template.format(u=val_a, b=val_b, v=val_a, c=val_b)
    return True, ""


def validate_full_update(field: str, value, current_state: SessionState) -> tuple[bool, str]:
    """Pipeline completo: campo individual + cross-fields."""
    ok, msg = validate_update_field(field, value, current_state)
    if not ok:
        return False, msg

    new_state = dataclasses.replace(current_state, **{field: value})
    return validate_cross_fields(new_state)


def check_finalization_checklist_items(state: SessionState) -> list[dict]:
    """Retorna lista de 12 items de checklist §7 con status."""
    # ... implementacion ...
    pass
```

### 2.5 `__init__.py`

```python
import dataclasses
from pathlib import Path

from . import _config
from .state import load_state, save_state, SessionState

# Cache de estado: {session_id: (state, mtime_ns)}
_state_cache: dict[str, tuple[SessionState, int]] = {}


def register(ctx):
    """Entry point del plugin."""
    ctx.register_command("sbtdd", handler=_make_sbtdd_handler(ctx))
    ctx.register_command("sbtdd-init", handler=_make_sbtdd_init_handler(ctx))
    ctx.register_command("sbtdd-check", handler=_make_sbtdd_check_handler(ctx))

    ctx.register_tool("sbtdd_status", schema=SCHEMA_STATUS, handler=_make_status_handler(ctx))
    ctx.register_tool("sbtdd_update_state", schema=SCHEMA_UPDATE_STATE, handler=_make_update_state_handler(ctx))

    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("on_session_start", _on_session_start)


def _get_cached_state(session_id: str, path: Path) -> SessionState:
    """Lee state con cache basado en mtime_ns."""
    import time
    if session_id in _state_cache:
        cached_state, cached_mtime = _state_cache[session_id]
        current_mtime = path.stat().st_mtime_ns if path.exists() else 0
        if current_mtime == cached_mtime:
            return cached_state
    state = load_state(path)
    mtime = path.stat().st_mtime_ns if path.exists() else 0
    _state_cache[session_id] = (state, mtime)
    return state


def _on_pre_tool_call(session_id, tool_name, tool_args, **kwargs):
    """Hook TDD-Guard: bloquea writes violatorios segun fase."""
    state = _get_cached_state(session_id, Path(".hermes/session-state.json"))

    if tool_name not in _config.TDDGUARD_TOOL_NAMES:
        return {"blocked": False}

    # Check override scoped
    override = state.tdd_guard_override
    if override and override.get("tool") == tool_name:
        if "path" in override:
            if tool_args.get("path", "") != override["path"]:
                return {"blocked": True, "reason": "Override scoped to different path"}

        # Consumir override (one-shot)
        new_state = dataclasses.replace(state, tdd_guard_override={})
        save_state(Path(".hermes/session-state.json"), new_state, expected_revision=state.state_revision)
        return {"blocked": False}

    # Heuristica TDD-Guard
    # ... implementacion ...
    pass


def _on_session_start(session_id, **kwargs):
    """Hook de sesion: inicializa estado."""
    # ... implementacion ...
    pass


# Schemas de tools (pendientes de definir)
SCHEMA_STATUS = {}  # TODO
SCHEMA_UPDATE_STATE = {}  # TODO
```

---

## 3. Scripts Auxiliares

### 3.1 `verify.py`
```python
import subprocess
import sys
from pathlib import Path

# ... implementacion de run_with_error_handling() ...
# ... lee templates/verification/{stack}.md y ejecuta comandos ...
```

### 3.2 `git_status.py`
```python
import subprocess
import json
import sys

# ... ejecuta git status, git log, parsea output ...
```

### 3.3 `drift_check.py`
```python
import json
import subprocess
import sys
from pathlib import Path

# ... lee state, ejecuta git log, detecta drift ...
```

### 3.4 `commit_helper.py`
```python
import sys

# ... recibe phase + descripcion, retorna mensaje sugerido ...
```

---

## 4. Templates y Referencias

- `HERMES.local.md.tmpl` — ~200 lineas (esencial)
- `spec-behavior-base.tmpl.md` — Seed de spec
- `verification/{rust,python,cpp}.md` — Comandos §0.1
- `references/*.md` — Documentacion instructiva para LLM

---

## 5. Tests

- `test_plugin.py` — Registro de commands, tools, hooks
- `test_state.py` — SessionState, load/save, OCC, migrate, corrupt file
- `test_validator.py` — Prefijos, mensajes, transiciones, cross-fields
- `test_magi_parser.py` — Parseo, timeout, ReDoS
- `test_scripts.py` — verify, git_status, drift_check
- `test_config.py` — Constantes, state machine
- `test_concurrency.py` — OCC concurrente, filelock

---

## 6. Tareas de Implementacion

```
Task 1: Scaffolding del paquete (EN PROGRESO)
  - Crear directorio sbtdd_hermes/ con __init__.py vacio
  - Crear plugin.yaml, pyproject.toml
  - Crear skeleton de todos los modulos

Task 2: Modulos core (state, validator, _config)
  - state.py: SessionState + load/save/migrate con todos los fixes MAGI
  - validator.py: Validacion pura
  - _config.py: Constantes centralizadas

Task 3: MAGI parser + scripts auxiliares
  - magi_parser.py: Regex seguras + multiprocessing timeout
  - scripts/: verify, git_status, drift_check, commit_helper

Task 4: Entry point + commands + hook
  - __init__.py: register() + _on_pre_tool_call + _on_session_start
  - commands.py: 3 slash command handlers
  - prompts.py: Generadores de prompts

Task 5: Templates y referencias
  - HERMES.local.md.tmpl (~200 lineas)
  - verification/*.md
  - references/*.md

Task 6: Tests
  - 7 archivos de tests unitarios

Task 7: Instalacion y prueba en Hermes
  - pip install -e .
  - Verificar carga sin errores
  - Verificar /sbtdd-check

Task 8: Documentacion y release
  - README.md
  - docs/migration-skill-to-plugin.md
  - Tag v2.0.0
```

---

**Archivo final:** `D:\jbolivarg\PythonProjects\SBTDD-Hermes\docs\implementation-plan-magi-revision.md` (FINAL)

**Estado:** IMPLEMENTANDO. Task 1 en progreso.
