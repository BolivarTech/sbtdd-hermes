# SBTDD-Hermes Plugin — Plan de Implementacion (Opcion C: Hibrido)

> **Arquitectura:** Plugin nativo Hermes (estado + orquestacion + TDD-Guard hook) + Scripts auxiliares Python (ejecutores de verificacion/git/MAGI) + Referencias instructivas para el LLM.
> **Referencia:** HERMES.local.md completo (797 lineas), plugin MAGI-Hermes (validado en produccion), documentacion oficial de Hermes Agent.

---

## 0. Principios Arquitectonicos (Opcion C)

| Capa | Responsabilidad | Que hace | Que NO hace |
|------|----------------|----------|-------------|
| **Plugin Nativo** (`sbtdd_hermes/*.py`) | Orquestacion + Estado + TDD-Guard | Decide que fase toca, valida commits, bloquea writes, lee/escribe state | NO ejecuta git, NO corre tests, NO invoca MAGI directamente |
| **Scripts Auxiliares** (`sbtdd_hermes/scripts/*.py`) | Ejecucion de operaciones complejas | Ejecutan `git status`, `cargo nextest`, parsean reportes MAGI, detectan drift | NO deciden la fase, NO escriben state (solo leen) |
| **Referencias** (`references/*.md`) | Guia instructiva para el LLM | Documentan el flujo SBTDD para que el agente sepa que hacer | NO contienen logica ejecutable |
| **Templates** (`templates/*.tmpl`) | Scaffolding inicial | Generan HERMES.local.md, spec-behavior-base.md | NO son la fuente de verdad del flujo |

**Regla de oro:** El plugin decide *qué* hacer; los scripts deciden *cómo* hacerlo; el agente (Hermes) ejecuta ambos via sus tools (`terminal`, `execute_code`).

---

## 1. Estructura del Paquete

```
sbtdd-hermes-plugin/
├── pyproject.toml                    # Entry-point: hermes_agent.plugins
├── plugin.yaml                       # Metadata del plugin
├── sbtdd_hermes/
│   ├── __init__.py                   # Entry point: register(ctx)
│   ├── commands.py                   # Handlers /sbtdd, /sbtdd-init, /sbtdd-check
│   ├── state.py                      # SessionState + load/save/drift
│   ├── validator.py                  # Validacion de commits, prefijos, checklist
│   ├── prompts.py                    # Generadores de prompts/instrucciones para el agente
│   ├── scaffolding.py                # Init logic (stack detection, template rendering)
│   ├── magi_parser.py                # Parser de reportes MAGI ASCII -> dict
│   └── scripts/                      # Scripts auxiliares ejecutables
│       ├── verify.py               # Ejecuta verificacion §0.1 por stack
│       ├── git_status.py           # Ejecuta git status + git log + analiza commits
│       ├── drift_check.py          # Detecta drift entre state y git log
│       └── commit_helper.py      # Genera mensajes de commit sugeridos
├── templates/
│   ├── HERMES.local.md.tmpl        # ~200 lineas (esencial: §0, §1, §2, §4, §5)
│   ├── spec-behavior-base.tmpl.md  # Seed de spec
│   └── verification/
│       ├── rust.md                   # Comandos §0.1 Rust
│       ├── python.md                 # Comandos §0.1 Python
│       └── cpp.md                    # Comandos §0.1 C/C++
├── references/                       # Documentacion instructiva para el LLM
│   ├── routing.md                    # Phase detection + artifact map
│   ├── review-gates.md             # Gate criteria + MAGI integration
│   ├── tdd-cycle.md                # TDD procedure + TDD-Guard behavior
│   ├── finalization.md             # Checklist §7
│   └── port-claude-to-hermes.md     # Migration notes
└── tests/
    ├── test_plugin.py
    ├── test_state.py
    ├── test_validator.py
    ├── test_magi_parser.py
    └── test_scripts.py
```

---

## 2. Plugin Nativo (`sbtdd_hermes/`)

### 2.1 Entry Point (`__init__.py`)

```python
def register(ctx):
    # Slash commands (el usuario los invoca explicitamente)
    ctx.register_command("sbtdd",       handler=_make_sbtdd_handler(ctx))
    ctx.register_command("sbtdd-init",  handler=_make_sbtdd_init_handler(ctx))
    ctx.register_command("sbtdd-check", handler=_make_sbtdd_check_handler(ctx))
    
    # Tool: el LLM puede invocarlo para consultar estado
    ctx.register_tool(
        "sbtdd_status",
        schema=SCHEMA_STATUS,
        handler=_make_status_handler(ctx),
    )
    
    # Hook TDD-Guard: bloquea writes violatorios (HEURISTICO)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    
    # Hook de sesion: inicializa estado al arrancar
    ctx.register_hook("on_session_start", _on_session_start)
```

**`_on_pre_tool_call(session_id, tool_name, tool_args, **kwargs)`**
- Lee `.hermes/session-state.json` via `pathlib`.
- Si `current_phase == "red"` y `tool_name` es `write_file`/`patch`:
  - Heuristica: si el path NO contiene `test` o `tests/` → bloquear con razon.
  - Si el path contiene `test` o `tests/` → permitir (es test).
- Si `current_phase == "green"` y el path contiene `test` o `tests/` → bloquear (no modificar tests en Green).
- Si `current_phase == "refactor"` y se detecta nueva funcionalidad (heuristica: nuevos archivos fuera de `tests/`) → advertencia.
- Retorna `{"blocked": True, "reason": "TDD-Red: cannot write production code"}` o `{"blocked": False}`.

**Nota sobre heuristica:** Documentada en `references/tdd-cycle.md` como "guard rail cooperativo, no fail-closed perfecto". El usuario puede forzar con `/sbtdd --override-guard`.

**`_on_session_start(session_id, **kwargs)`**
- Lee `~/.hermes/HERMES.md` y `./.hermes/HERMES.local.md`.
- Si existe `.hermes/session-state.json` → leer y reportar estado.
- Si no existe y hay plan aprobado → crear state inicial.

### 2.2 Commands (`commands.py`)

**`/sbtdd [--ollama]`**
1. Leer `.hermes/session-state.json`.
2. Invocar `orchestrator.detect_phase()` → retorna fase (string).
3. Construir prompt con:
   - Fase detectada + razonamiento.
   - Instrucciones especificas de la fase (de `references/routing.md`).
   - Comandos sugeridos para el agente ejecutar (via `prompts.py`).
4. Retornar prompt al usuario (el agente lo ejecuta).

**`/sbtdd-init [--ollama-init]`**
1. `scaffolding.detect_stack()` → detecta stack.
2. `scaffolding.render_hermes_local_md()` → genera `HERMES.local.md`.
3. `scaffolding.merge_gitignore()` → actualiza `.gitignore`.
4. `scaffolding.create_directories()` → crea `sbtdd/`, `planning/`.
5. `scaffolding.seed_spec_behavior_base()` → copia template.
6. Opcional `--ollama-init`: delegar a `magi_plugin.ollama_init` si disponible.
7. Retornar tabla Markdown de resumen.

**`/sbtdd-check`**
1. Ejecuta scripts auxiliares via `subprocess.run()` (el plugin SI puede ejecutar scripts locales):
   ```python
   subprocess.run(["python", "-m", "sbtdd_hermes.scripts.verify", "--check-only"])
   subprocess.run(["python", "-m", "sbtdd_hermes.scripts.drift_check"])
   subprocess.run(["python", "-m", "sbtdd_hermes.scripts.git_status", "--check"])
   ```
2. Agrega checks del propio plugin:
   - HERMES.local.md presente?
   - sbtdd/ y planning/ existen?
   - Plugin SBTDD registrado?
3. Retornar tabla Markdown con 8 checks.

**Nota importante:** El plugin SI puede ejecutar scripts Python propios via `subprocess.run()` o `importlib`. Lo que NO puede es ejecutar `git` o `cargo` directamente en el hook, pero puede hacerlo en el handler del slash command.

### 2.3 State (`state.py`)

Dataclass `SessionState` con 10 campos (§2.2 + §6.1):
```python
@dataclass
class SessionState:
    plan_path: str = "planning/hermes-plan-tdd.md"
    current_task_id: str | None = None
    current_task_title: str | None = None
    current_phase: str = "red"          # "red" | "green" | "refactor" | "done"
    phase_started_at_commit: str = ""
    last_verification_at: str | None = None
    last_verification_result: str | None = None
    # §6.1 presupuesto MAGI
    magi_iteration_budget: int | None = None
    magi_iterations_used: int = 0
    magi_target_verdict: str | None = None
```

Metodos:
- `load_state(path) -> SessionState` — §2.3: lee sin modificar si existe; crea si no.
- `save_state(path, state) -> None` — §2.3: escribe JSON.
- `detect_drift(state, git_log) -> tuple[str, str | None]` — §2.1: tabla canonica + 5 clasificaciones.
- `advance_task(state, plan_path) -> SessionState` — §2.3: avanza al siguiente `[ ]`, reset "red".
- `close_plan(state) -> SessionState` — §2.3: pone todo a null/done.

### 2.4 Validator (`validator.py`)

Validacion PURA (solo strings, no ejecuta comandos):

```python
COMMIT_PREFIXES = {
    "red": ["test:"],
    "green": ["feat:", "fix:"],
    "refactor": ["refactor:"],
    "close_task": ["chore:"],
    "review_fix": ["test:", "fix:", "refactor:"],
}

COMMIT_MESSAGE_RULES = {
    "language": "english",
    "max_length": 72,
    "mood": "imperative",
    "no_ai_refs": True,
    "no_co_authored_by": True,
}

MAGI_VERDICTS = {
    "STRONG GO": {"action": "proceed", "re_evaluate": False},
    "GO": {"action": "proceed", "re_evaluate": False},
    "GO WITH CAVEATS": {"action": "apply_conditions", "re_evaluate": "conditional"},
    "HOLD -- TIE": {"action": "blocked", "re_evaluate": True},
    "HOLD": {"action": "blocked", "re_evaluate": True},
    "STRONG NO-GO": {"action": "replan", "re_evaluate": True},
}
```

Metodos:
- `validate_commit_prefix(message: str, phase: str) -> tuple[bool, str]` — §5: verifica prefijo-fase.
- `validate_commit_message(message: str) -> tuple[bool, list[str]]` — §5: ingles, <=72, sin AI, sin Co-Authored-By.
- `validate_commit_atomicity(diff: str) -> tuple[bool, str]` — §5: single-purpose.
- `is_commit_authorized_under_plan(message: str, state: SessionState) -> bool` — §5.1: verifica plan aprobado.
- `check_finalization_checklist_items() -> list[dict]` — §7: retorna lista de 12 items con status.
- `parse_magi_verdict(report: str) -> tuple[str, dict]` — Delega a `magi_parser.py`.

### 2.5 Prompts (`prompts.py`)

Generadores de prompts/instrucciones para el agente. El plugin NO ejecuta, SOLO genera texto:

- `build_phase_prompt(phase: str, state: SessionState) -> str` — Genera instrucciones segun fase.
- `build_verification_prompt(stack: str) -> str` — Genera comandos §0.1 a ejecutar.
- `build_git_status_prompt() -> str` — Genera instrucciones para `git status`.
- `build_commit_suggestion(phase: str, task_id: str, description: str) -> str` — Genera mensaje de commit sugerido.
- `build_pre_merge_checklist() -> str` — Genera checklist de 12 items.
- `build_magi_payload(spec_path: Path, plan_path: Path) -> str` — Genera payload para `/skill magi`.

### 2.6 Scaffolding (`scaffolding.py`)

- `detect_stack(root: Path) -> str | None` — §4: detecta manifest.
- `render_hermes_local_md(stack: str, author: str | None, error_type: str | None) -> str` — Renderiza template.
- `merge_gitignore(root: Path, entries: list[str]) -> tuple[list, list, list]` — §1.1: idempotente.
- `create_directories(root: Path, dirs: list[str]) -> list[str]` — Crea dirs.
- `seed_spec_behavior_base(root: Path) -> str` — Copia template.
- `scaffold_ollama_config(root: Path) -> str` — Delega a magi_plugin.

### 2.7 MAGI Parser (`magi_parser.py`)

Parser del formato ASCII canonico de MAGI:

```python
def parse_magi_report(report: str) -> dict:
    """
    Extrae de un reporte MAGI ASCII:
    - veredicto: str (ej. "GO WITH CAVEATS")
    - consensus: dict {melchior: {...}, balthasar: {...}, caspar: {...}}
    - findings: list[dict] (critical/warning/info)
    - conditions: list[str]
    - recommended_actions: list[str]
    - dissent: str | None
    """
```

Implementa regex/line parsing para el formato canonico del banner MAGI (52 columnas, veredictos, findings).

---

## 3. Scripts Auxiliares (`sbtdd_hermes/scripts/`)

### 3.1 `verify.py` — Verificacion §0.1

Ejecuta comandos de verificacion por stack y reporta resultados:

```bash
python -m sbtdd_hermes.scripts.verify --stack rust
python -m sbtdd_hermes.scripts.verify --stack python
python -m sbtdd_hermes.scripts.verify --stack cpp
python -m sbtdd_hermes.scripts.verify --check-only  # para /sbtdd-check
```

Implementacion:
- Lee `templates/verification/{stack}.md` para obtener lista de comandos.
- Ejecuta cada comando via `subprocess.run()`.
- Reporta: PASSED/FAILED para cada comando + output capturado.
- Retorna exit code 0 si todos pasan, 1 si alguno falla.

### 3.2 `git_status.py` — Analisis de Git

```bash
python -m sbtdd_hermes.scripts.git_status --check        # para /sbtdd-check
python -m sbtdd_hermes.scripts.git_status --log -n 5   # ultimos 5 commits
python -m sbtdd_hermes.scripts.git_status --last-prefix  # prefijo del ultimo commit
```

Implementacion:
- Ejecuta `git status`, `git log --oneline -n N`, `git log --format=%s -1`.
- Parsea output para extraer: archivos modificados, staged, untracked, ultimo prefijo de commit.
- Retorna JSON para facil consumo por el plugin.

### 3.3 `drift_check.py` — Deteccion de Drift

```bash
python -m sbtdd_hermes.scripts.drift_check --state .hermes/session-state.json
```

Implementacion:
- Lee `session-state.json` + ejecuta `git log --format=%s -1`.
- Aplica tabla canonica de mapeo commit-prefix -> expected phase.
- Clasifica en: CONSISTENT, RECOVERABLE_LAG, DRIFT, UNRECOGNISED, N/A.
- Retorna JSON con clasificacion + razonamiento.

### 3.4 `commit_helper.py` — Sugerencias de Commit

```bash
python -m sbtdd_hermes.scripts.commit_helper --phase red --task "parser edge cases"
# Output: "test: add parser edge case for empty input"
```

Implementacion:
- Recibe phase + descripcion.
- Aplica reglas de prefijo + formato.
- Retorna mensaje sugerido.

---

## 4. Templates

### 4.1 `HERMES.local.md.tmpl` (~200 lineas)

**Contenido esencial** (las secciones procedurales §3, §6, §7 se eliminan del template y viven en el plugin):

```markdown
# HERMES.local.md — Reglas SBTDD

## 0. Mandatory Code Standards
- Leer `~/.hermes/HERMES.md` primero (precedencia absoluta)
- §0.1 Per-phase verification (template inserta comandos segun stack)
- §0.2 Project-specific rules (ErrorType, Author, file headers)

## 1. Metodologia: SBTDD
- Jerarquia de documentos (tabla de 6+ archivos)
- Tracking policy: sbtdd/, planning/, .hermes/, HERMES.local.md NO se trackean

## 2. Artefactos y Estado
- Tabla de 4 artefactos (HERMES.local.md, session-state.json, git, plan)
- Orden de canon: Git > State > Plan
- Schema session-state.json (7 campos)
- Protocolo de escritura (apertura, cierre fase, cierre tarea, cierre plan)
- Drift detection: tabla canonica + 5 clasificaciones

## 4. Stack del Proyecto
- (filled by /sbtdd-init): lenguaje, test runner, comando test
- TDD-Guard: implementado via plugin nativo SBTDD (pre_tool_call hook)
  Requiere `sbtdd` en `plugins.enabled` de `~/.hermes/config.yaml`.

## 5. Git Commit Conventions
- Prefijos autorizados (tabla)
- Excepcion bajo plan aprobado (4 categorias)
- Reglas adicionales (ingles, sin IA, sin Co-Authored-By, atomicos)
- Remotos: origin + NAS (opcional)
```

**Nota:** Las secciones §3 (Ciclo TDD), §6 (Code Review), §6.1 (Correccion autonoma), §7 (Finalizacion) son **procedurales** y viven en el **codigo del plugin** + `references/*.md`, no en el template. Esto evita que el template sea un monolito de 797 lineas y permite que el plugin evolucione sin tocar los archivos generados.

### 4.2 Otros templates
- `spec-behavior-base.tmpl.md` — Igual al original.
- `verification/{rust,python,cpp}.md` — Comandos §0.1.

---

## 5. Referencias (para el LLM)

| Archivo | Contenido | Reglas cubiertas |
|---------|-----------|------------------|
| `references/routing.md` | Phase detection + artifact map + drift recovery | §1, §2 |
| `references/review-gates.md` | Gate criteria + MAGI integration + dual-loop + correction | §6, §6.1 |
| `references/tdd-cycle.md` | Per-phase rules + TDD-Guard behavior + atomic close | §3 |
| `references/finalization.md` | Git status check + checklist 12 items | §7 |
| `references/port-claude-to-hermes.md` | Migration notes + adaptaciones | Todas |

---

## 6. Trazabilidad HERMES.local.md -> Opcion C

### §0 — Mandatory Standards
- `templates/HERMES.local.md.tmpl` (secciones §0.1, §0.2)
- `templates/verification/{rust,python,cpp}.md` (comandos §0.1)
- `scripts/verify.py` (ejecutor de comandos §0.1)

### §1 — Metodologia
- `references/routing.md` (flujo de especificacion)
- `orchestrator.detect_phase()` (routing)
- `prompts.build_phase_prompt()` (instrucciones por fase)

### §2 — Artefactos
- `state.py` (SessionState, schema, protocolo)
- `scripts/drift_check.py` (deteccion de drift)
- `references/routing.md` (tabla canonica, 5 clasificaciones)

### §3 — Ciclo TDD
- `__init__._on_pre_tool_call()` (TDD-Guard hook)
- `references/tdd-cycle.md` (reglas por fase, cierre atomico)
- `validator.validate_commit_prefix()` (prefijos §5)
- `scripts/commit_helper.py` (mensajes sugeridos)

### §4 — Stack
- `scaffolding.detect_stack()` (deteccion)
- `templates/HERMES.local.md.tmpl` (seccion §4)

### §5 — Git
- `validator.py` (COMMIT_PREFIXES, COMMIT_MESSAGE_RULES, categorias autorizadas)
- `templates/HERMES.local.md.tmpl` (seccion §5 completa)
- `scripts/git_status.py` (analisis de git)

### §6 — Code Review
- `references/review-gates.md` (dual-loop, tabla veredictos)
- `magi_parser.py` (parser de reportes MAGI)
- `prompts.build_pre_merge_checklist()` (checklist)

### §6.1 — Correccion Autonoma
- `state.py` (magi_iteration_budget, magi_iterations_used, magi_target_verdict)
- `references/review-gates.md` (presupuesto, protocolo, condiciones de parada)

### §7 — Finalizacion
- `validator.check_finalization_checklist_items()` (12 items)
- `scripts/git_status.py` (verificacion git status limpio)
- `references/finalization.md` (procedimiento)

---

## 7. Tareas y Dependencias (Opcion C)

```
Task 1: Scaffolding del paquete plugin
  - Crear directorio sbtdd_hermes/ con __init__.py vacio
  - Crear plugin.yaml, pyproject.toml
  - Depende de: nada
  - Bloquea: Task 2, Task 3

Task 2: Implementar scripts auxiliares (independientes)
  - scripts/verify.py (verificacion §0.1)
  - scripts/git_status.py (analisis git)
  - scripts/drift_check.py (deteccion drift)
  - scripts/commit_helper.py (sugerencias commit)
  - Depende de: nada
  - Bloquea: Task 4

Task 3: Implementar modulos core del plugin (puros, no dependen de scripts)
  - state.py (SessionState + load/save/drift)
  - validator.py (validacion de commits + checklist §7)
  - prompts.py (generadores de prompts)
  - scaffolding.py (init logic)
  - magi_parser.py (parser MAGI)
  - Depende de: nada
  - Bloquea: Task 4

Task 4: Integrar entry point + handlers + hook
  - __init__.py (register + _on_pre_tool_call + _on_session_start)
  - commands.py (3 slash command handlers)
  - Conectar con modulos core
  - Depende de: Task 1, Task 2, Task 3
  - Bloquea: Task 5

Task 5: Templates y referencias
  - HERMES.local.md.tmpl (~200 lineas)
  - spec-behavior-base.tmpl.md
  - verification/*.md
  - references/*.md
  - Depende de: Task 3 (scaffolding necesita templates)
  - Bloquea: Task 6

Task 6: Tests unitarios
  - test_plugin.py, test_state.py, test_validator.py
  - test_magi_parser.py, test_scripts.py
  - Depende de: Task 4, Task 5
  - Bloquea: Task 7

Task 7: Instalacion y prueba en Hermes
  - pip install -e . (o copiar a ~/.hermes/plugins/sbtdd/)
  - Verificar que plugin carga sin errores
  - Verificar /sbtdd-check en repo de prueba
  - Verificar hook pre_tool_call bloquea writes
  - Depende de: Task 6
  - Bloquea: Task 8

Task 8: Documentacion y release
  - README.md (instalacion, uso, arquitectura)
  - docs/migration-skill-to-plugin.md
  - Tag v2.0.0 + release GitHub
  - Depende de: Task 7
```

---

## 8. Decisiones de Diseno Criticas (Opcion C)

| Decision | Rationale |
|----------|-----------|
| Plugin = orquestador, scripts = ejecutores | Hermes NO permite al plugin ejecutar terminal/git directamente en hooks, pero SI permite ejecutar scripts Python propios desde slash commands |
| TDD-Guard heurístico (no perfecto) | Imposible determinar 100% si un write es "test" vs "prod" sin parsear AST. La heuristica (ruta contiene `test`) es buena suficiente y documentada |
| Template HERMES.local.md de ~200 lineas | Las reglas procedurales (§3, §6, §7) viven en el plugin para permitir actualizaciones sin tocar archivos generados |
| Scripts como modulos ejecutables (`python -m`) | Permiten invocarlos desde el plugin via `subprocess.run()` y tambien desde terminal manualmente |
| MAGI parser separado (`magi_parser.py`) | El formato ASCII de MAGI es canonico y parseable. Separar el parser facilita tests y reutilizacion |
| Estado en `.hermes/session-state.json` | Coherente con HERMES.local.md §2.2. El plugin lee/escribe directamente; los scripts solo leen |
| `/sbtdd-check` ejecuta scripts auxiliares | El slash command handler SI tiene contexto para ejecutar subprocess (a diferencia del hook) |
