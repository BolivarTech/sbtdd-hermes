# Analisis de Implementabilidad: SBTDD-Hermes Plugin en Entorno Hermes

## Hallazgos de la Investigacion del API de Plugins de Hermes

Fuentes: Documentacion oficial de Hermes Agent (hermes-agent.nousresearch.com/docs) + codigo fuente del plugin MAGI-Hermes (ya funcionando en produccion).

### Hooks Disponibles en Hermes

| Hook | Cuando se ejecuta | Puede bloquear? | Uso en SBTDD |
|------|-------------------|-----------------|--------------|
| `pre_tool_call` | Antes de cada tool execution | **SI** — retorna `{"blocked": true}` para vetar | TDD-Guard: bloquear write_file/patch/terminal en fase incorrecta |
| `post_tool_call` | Despues de cada tool execution | NO | Logging/auditoria |
| `pre_llm_call` | Antes de cada LLM inference | NO — solo inyecta contexto | Detectar triggers "TDD-Red:", sugerir TDD-Guard |
| `post_llm_call` | Despues de cada LLM inference | NO | Logging |
| `on_session_start` | Al iniciar sesion | NO | Leer HERMES.md, inicializar estado |
| `on_session_end` | Al cerrar sesion | NO | Cleanup |
| `transform_llm_output` | Transforma salida del LLM | NO | No necesario para SBTDD |

**Hook NO disponible**: `UserPromptSubmit` (existe en Claude, no en Hermes). El toggle `TDD-Guard ON/OFF` debe hacerse via `/sbtdd` command o detectando patrones en `pre_llm_call`.

---

## Problemas Criticos Encontrados

### Problema 1: TDD-Guard no puede determinar "codigo de produccion" vs "tests" con certeza

**El plan asume:** `enforce_tdd_phase()` puede decidir si `write_file` esta creando un test o codigo de produccion basandose en el nombre del archivo.

**Realidad:** Esto es HEURISTICO. Un archivo llamado `test_parser.py` es obviamente un test. Pero `parser_test.py` podria ser un test o un modulo de utilidades de test. `utils.py` podria contener tests o helpers.

**Mitigacion:**
- Usar convenciones de nombre (archivos que contengan `test_` o `_test.py` = tests; `tests/` directorio = tests).
- Documentar claramente en `references/tdd-cycle.md` que el TDD-Guard es un "guard rail" con falsos positivos posibles.
- El agente siempre puede sobrescribir con `/sbtdd --override-guard`.
- **Importante:** El TDD-Guard es **cooperativo**, no **fail-closed perfecto**.

### Problema 2: El plugin NO puede ejecutar comandos Git ni terminal directamente

**El plan asume:** `orchestrator.atomic_commit()`, `validator.check_git_status()`, `state.recover_state()` ejecutan `git status`, `git log`, `cargo nextest run`, etc.

**Realidad:** Los plugins de Hermes NO tienen acceso directo a terminal/git/subprocess. Los plugins registran:
- `ctx.register_command()` → slash commands que retornan strings
- `ctx.register_tool()` → tools que Hermes puede invocar (el LLM decide cuando usarlas)
- `ctx.register_hook()` → hooks que interceptan eventos

**Mitigacion:**
- El plugin DEBE devolver **instrucciones al agente** para que ejecute los comandos via sus propios tools (`terminal`, `write_file`, etc.).
- Los metodos del plugin que "ejecutan" comandos deben ser **generadores de prompts/instrucciones**, no ejecutores.
- Ejemplo: `validator.check_git_status()` → retorna string "Ejecutar `git status` y verificar que no haya archivos modificados..."

### Problema 3: El plugin NO puede crear commits de Git

**El plan asume:** El plugin puede crear commits atomicos (`test:`, `feat:`, `refactor:`).

**Realidad:** El plugin NO puede ejecutar `git commit`. El agente (Hermes) es quien ejecuta `terminal` tool.

**Mitigacion:**
- El plugin provee **templates de mensajes de commit** y **checklist de validacion**.
- El handler `/sbtdd` puede generar el mensaje de commit correcto basado en la fase.
- El agente debe ser instruido a usar el mensaje sugerido por el plugin.
- **Diseño:** El plugin es **orquestador/asistente**, no **ejecutor**.

### Problema 4: `pre_tool_call` se ejecuta en el contexto del hook, no en el del agente

**El plan asume:** `_on_pre_tool_call()` puede leer archivos del proyecto (`.hermes/session-state.json`) y analizarlos.

**Realidad:** El hook `pre_tool_call` recibe argumentos limitados. Segun la documentacion:
```python
def _on_pre_tool_call(session_id, tool_name, tool_args, **kwargs):
```

No tiene acceso directo al filesystem ni al `ctx` (el `ctx` solo esta disponible en `register()`). Sin embargo, el hook puede importar modulos y leer archivos directamente (es codigo Python).

**Mitigacion:**
- El hook puede leer `.hermes/session-state.json` via `pathlib` directamente (no necesita `ctx`).
- Usar ruta relativa al directorio de trabajo (que es el proyecto donde corre Hermes).
- Cachear el estado para evitar lectura de disco en cada tool call.

### Problema 5: MAGI retorna un string/report, no datos estructurados

**El plan asume:** `orchestrator.pre_merge_loop_2()` puede procesar findings de MAGI, clasificarlos, contar iteraciones, etc.

**Realidad:** MAGI (`/skill magi` o `magi_analyze` tool) retorna un reporte ASCII/string. El plugin necesitaria parsear ese string para extraer veredictos y findings.

**Mitigacion:**
- El plugin puede proporcionar un **parser** del formato MAGI (que es canonico y conocido).
- Alternativa: El plugin no procesa MAGI automaticamente; solo presenta el reporte y pide al usuario que indique el veredicto.
- **Diseno realista:** El plugin orquesta el **flujo** (cuando invocar MAGI, cuantas iteraciones), pero el **parseo** es manual o via LLM.

### Problema 6: El template HERMES.local.md.tmpl de 797 lineas es excesivo

**El plan asume:** El template contiene TODAS las reglas del HERMES.local.md del usuario (797 lineas).

**Realidad:** El template de SBTDD-Skill original (`CLAUDE.local.md.tmpl`) es de **339 lineas** y intencionalmente OMITE §3, §6, §7. El HERMES.local.md del usuario es un **documento vivo** que el usuario mantiene manualmente.

**Mitigacion:**
- El template del plugin debe ser una **plantilla base** con las secciones esenciales (§0, §1, §2, §4, §5), NO un documento de 797 lineas.
- Las secciones procedurales (§3, §6, §7) deben vivir en el **codigo del plugin** y en `references/`.
- El usuario siempre puede personalizar su `HERMES.local.md` despues del init.
- **Diseño:** El template es un **scaffold**, no un **clon exacto**.

### Problema 7: `/sbtdd-check` Check 7 "Skills requeridos disponibles"

**El plan asume:** El plugin puede verificar que skills como `plan`, `test-driven-development`, `magi` esten instalados.

**Realidad:** Los plugins NO tienen API para listar skills instalados. Hermes maneja skills internamente.

**Mitigacion:**
- Documentar los prerequisitos en el README.
- El check puede intentar invocar el skill y reportar si falla.
- O simplemente **eliminar** Check 7 del plan.

---

## Limitaciones Arquitectonicas del Ecosistema Hermes

| Capacidad | Claude | Hermes | Impacto en SBTDD Plugin |
|-----------|--------|--------|------------------------|
| `PreToolUse` hook con `blocked: true` | ✅ Nativo | ✅ `pre_tool_call` con `blocked: true` | TDD-Guard implementable |
| `SessionStart` hook | ✅ Nativo | ✅ `on_session_start` | Inicializacion de estado implementable |
| `UserPromptSubmit` hook | ✅ Nativo | ❌ No existe | Toggle TDD-Guard debe ser via `/sbtdd` command |
| Ejecutar terminal/git desde plugin | ❌ (solo via hooks) | ❌ (solo via agente) | Plugin es orquestador, no ejecutor |
| Skills enumerables desde plugin | ❌ | ❌ | Check 7 debe eliminarse o simplificarse |
| Subagentes con modelos distintos | ❌ | ❌ | Documentar limitacion en `references/` |
| `settings.json` con hooks | ✅ Nativo | ❌ No existe | TDD-Guard via `pre_tool_call` nativo |

---

## Analisis por Modulo del Plan

### `__init__.py` — Implementable con ajustes

- ✅ `register(ctx)` con 3 commands + 1 tool + hook `pre_tool_call` → **implementable**
- ⚠️ `_on_pre_tool_call()` necesita ser **hook** (no handler): lee `session-state.json`, aplica heuristica de tests vs prod → **implementable con limitaciones**
- ❌ Toggle `TDD-Guard ON/OFF` via prompt detection → **NO implementable**. Usar `/sbtdd --tdd-guard-on` y `/sbtdd --tdd-guard-off` commands en su lugar.

### `state.py` — Implementable

- ✅ Dataclass `SessionState` con 7 campos + 3 de §6.1 → **implementable**
- ✅ `load_state()`, `save_state()` via `pathlib` + `json` → **implementable**
- ✅ `detect_drift()` con tabla canonica + 5 clasificaciones → **implementable**
- ⚠️ `advance_task()`, `close_plan()` → **solo actualizan estructuras de datos**. El agente debe ejecutar el commit.

### `orchestrator.py` — Parcialmente implementable (requiere rediseño)

- ✅ `detect_phase()` → **implementable** (lee archivos, retorna fase)
- ✅ `run_brainstorm()` → **implementable** (construye prompt, retorna instrucciones al agente)
- ⚠️ `plan_gate_checkpoint_1()` → **implementable como prompt**. Presenta plan al usuario, espera input. NO puede "esperar" automaticamente; el flujo es conversacional.
- ⚠️ `plan_gate_checkpoint_2()` → **implementable con parser MAGI**. Invoca `/skill magi` via tool call, parsea resultado.
- ❌ `pre_merge_loop_1()`, `pre_merge_loop_2()` → **NO implementables como metodos autonomos**. Son **flujos conversacionales** que el agente ejecuta paso a paso. El plugin puede proveer un **checklist** y **recordar estado** entre turnos.
- ❌ `autonomous_correction_loop()` → **NO implementable como loop automatico**. Hermes no tiene "autonomia" para iterar sin intervencion del usuario (a menos que el usuario de permiso explicito por turno).
- ⚠️ `finalization_phase()` → **implementable como checklist**. Valida condiciones, retorna items pendientes.

### `validator.py` — Implementable con ajustes

- ✅ Constantes `COMMIT_PREFIXES`, `COMMIT_MESSAGE_RULES`, `MAGI_VERDICTS` → **implementables**
- ✅ `validate_commit_prefix()`, `validate_commit_message()`, `validate_commit_atomicity()` → **implementables** (operan sobre strings)
- ⚠️ `run_verification()` → **NO puede ejecutar comandos directamente**. Debe retornar instrucciones al agente.
- ⚠️ `enforce_tdd_phase()` → **implementable con heuristica**. NO es infalible.
- ⚠️ `check_git_status()` → **NO puede ejecutar `git status` directamente**. Debe retornar instrucciones al agente.
- ✅ `check_finalization_checklist()` → **implementable** (oper sobre datos ya existentes)

### `scaffolding.py` — Implementable

- ✅ `detect_stack()` → **implementable** (lee archivos del proyecto)
- ✅ `render_hermes_local_md()` → **implementable** (string.Template o Jinja2)
- ✅ `merge_gitignore()` → **implementable** (manipulacion de archivos)
- ✅ `create_directories()`, `seed_spec_behavior_base()` → **implementables**
- ⚠️ `scaffold_ollama_config()` → **implementable** si `magi_plugin` esta instalado como pip package o directory plugin

### Templates — Implementables con ajustes

- ⚠️ `HERMES.local.md.tmpl` → **NO debe tener 797 lineas**. Usar plantilla base de ~200-300 lineas con secciones esenciales. Las reglas procedurales van en el codigo del plugin.
- ✅ `spec-behavior-base.tmpl.md`, `verification/*.md` → **implementables**

### Referencias — Implementables

- ✅ `routing.md`, `review-gates.md`, `tdd-cycle.md`, `finalization.md`, `port-claude-to-hermes.md` → **implementables** (documentacion instructiva para el LLM)

---

## Rediseño Recomendado del Plugin

### Principio rector

> **El plugin SBTDD es un ORQUESTADOR/ASISTENTE, no un EJECUTOR.**
>
> - Provee **estructura**, **comandos slash**, **checklist**, **validacion**, **estado persistente**.
> - NO ejecuta codigo, NO crea commits, NO corre tests directamente.
> - El agente (Hermes) es el ejecutor; el plugin es el director de orquesta.

### Arquitectura revisada

```
sbtdd_hermes/
  __init__.py              # Entry point: 3 slash commands + 1 tool + pre_tool_call hook
  plugin.yaml              # Metadata
  commands.py              # Handlers de /sbtdd, /sbtdd-init, /sbtdd-check
  state.py                 # SessionState + load/save/drift detection
  prompts.py               # Generadores de prompts/instrucciones para el agente
  validator.py             # Validacion de commits, prefijos, fases (puros, no ejecutan)
  scaffolding.py           # Init logic (stack detection, template rendering)
  templates/
    HERMES.local.md.tmpl   # ~200 lineas (esencial), no 797
    ...
  references/              # Markdown instructivo
```

### Cambios especificos por modulo

#### `__init__.py`
- ✅ 3 slash commands: `/sbtdd`, `/sbtdd-init`, `/sbtdd-check`
- ✅ 1 tool: `sbtdd_status` (consulta estado actual)
- ✅ Hook `pre_tool_call`: bloquea `write_file`/`patch` en fase incorrecta (HEURISTICO)
- ✅ Hook `on_session_start`: lee HERMES.md + inicializa estado
- ❌ **Eliminar**: toggle via prompt detection. Reemplazar con `/sbtdd --tdd-guard-on/off`

#### `orchestrator.py`
- ✅ `detect_phase()`: retorna fase basada en artefactos
- ✅ `build_brainstorm_prompt()`: construye prompt para `/skill plan`
- ✅ `build_pre_merge_checklist()`: retorna checklist de items Loop 1 + Loop 2
- ✅ `parse_magi_verdict(report: str)`: extrae veredicto de reporte MAGI
- ❌ **Eliminar**: `plan_gate_checkpoint_1()` como "esperar aprobacion". Reemplazar con **prompt que presenta plan y pide input del usuario**.
- ❌ **Eliminar**: `autonomous_correction_loop()`. Reemplazar con **checklist de iteracion** que el usuario avanza manualmente.
- ❌ **Eliminar**: `pre_merge_loop_1()` y `_loop_2()` como loops automaticos. Reemplazar con **guia paso a paso**.

#### `validator.py`
- ✅ Validacion de strings (prefijos, mensajes, atomicidad)
- ✅ Checklist de finalizacion (12 items)
- ❌ **Eliminar**: `run_verification()` como ejecutor. Reemplazar con `build_verification_prompt(stack)` que retorna comandos a ejecutar.
- ❌ **Eliminar**: `check_git_status()` como ejecutor. Reemplazar con `build_git_status_check()` que retorna instrucciones.

#### Templates
- ⚠️ `HERMES.local.md.tmpl`: **reducir a ~200 lineas**. Incluir solo §0, §1, §2, §4, §5. Las reglas procedurales (§3, §6, §7) viven en el plugin.

---

## Conclusion

### Estado del plan actual

| Aspecto | Estado |
|---------|--------|
| Cobertura de reglas HERMES.local.md | ✅ 100% (90/90) |
| Implementabilidad tecnica en Hermes | ⚠️ ~60% (requiere rediseño significativo) |
| Realismo arquitectonico | ❌ Muy optimista (asume capacidades de ejecucion que Hermes no tiene) |

### Veredicto

El plan es **tecnicamente incompleto** para el entorno Hermes. Necesita un **rediseño** que reconozca que:

1. **El plugin es orquestador, no ejecutor.**
2. **Los hooks pueden bloquear pero no ejecutar.**
3. **Los slash commands retornan instrucciones, no ejecutan codigo.**
4. **El flujo SBTDD es conversacional, no autonomo.**

### Recomendacion

**Opcion A: Plugin puramente estructural (recomendado)**
- Estado persistente (`session-state.json`)
- Slash commands para scaffolding y checklist
- Hook `pre_tool_call` para TDD-Guard cooperativo (heuristico)
- Referencias instructivas para el LLM
- El agente ejecuta todo el trabajo

**Opcion B: Plugin con scripts auxiliares (mas complejo)**
- Ademas del plugin, proveer scripts Python que el agente puede ejecutar via `terminal`
- Los scripts hacen el trabajo pesado (verificacion, git status, drift detection)
- El plugin orquesta cuando ejecutar los scripts

**Opcion C: Hibrido (optimo)**
- Plugin nativo con estado + checklist + TDD-Guard hook
- Scripts auxiliares para operaciones que necesitan subprocess (git, cargo, pytest)
- El plugin decide que script ejecutar y cuando

**Mi recomendacion:** Opcion C. Mantiene la simplicidad del plugin nativo mientras delega operaciones complejas a scripts confiables.
