# Porting SBTDD from Claude to Hermes

## What Was Lost

The Claude ecosystem had three automatic hooks that enforced TDD discipline:

| Hook | Function | Hermes Equivalent |
|------|----------|-----------------|
| `PreToolUse` | Intercepted `NewFileTool` and `EditFileTool` | **None** |
| `SessionStart` | Reset state, read rules | Manual agent discipline |
| `UserPromptSubmit` | Detected `TDD-*:` prefixes, routed to phase handler | Explicit user prompt |

These hooks ran **before the agent acted**. In Hermes, the agent must choose to enforce the rules. This is a feature in some ways — the agent understands why it is enforcing discipline — but it requires discipline.

## What Was Gained

| Capability | Claude | Hermes |
|------------|--------|--------|
| Backend | Anthropic API only | Any OpenAI-compatible endpoint |
| Multi-model MAGI | Same model, prompt-only diversity | **Real cross-lineage diversity** |
| Cross-platform | Terminal only | Terminal + Telegram + Discord + Slack + ... |
| Memory | None | Persistent via Hermes memory system |
| Community | Closed | Open source (Hermes Agent by Nous Research) |

## The Five Adaptations

### 1. Hooks → Explicit User Declaration

**Claude:**
```
User: "Write a parser"
[PreToolUse intercepts, checks session-state.json, blocks if wrong phase]
```

**Hermes:**
```
User: "TDD-Red: write failing test for parser edge cases"
[Agent recognizes prefix, enters Red phase, writes test only]

User: "TDD-Green: make the tests pass"
[Agent writes minimum code to satisfy tests]

User: "TDD-Refactor: clean up the parser"
[Agent refactors with tests passing]
```

The agent must recognize the prefix and act accordingly. The user must use the prefix. This is a cooperative protocol.

### 2. TDD-Guard → Agent Discipline

**Claude:** TDD-Guard was a tool interceptor. If you tried to write production code during Red phase, it blocked the tool call.

**Hermes:** The agent must refuse. Example dialogue:

```
User: "Write the parser function now" (during Red phase)
Agent: "We are in TDD-Red phase. I can only write tests. If you want to skip ahead, declare TDD-Green:."
```

This is less robust than automatic interception but more transparent. The agent explains why it is refusing, which educates the user.

### 3. `.claude/CLAUDE.md` → `~/.hermes/HERMES.md`

Same function, different path. The global rules file lives in `~/.hermes/` instead of `.claude/`.

**Claude:**
```
.claude/
  CLAUDE.md          (global rules)
  CLAUDE.local.md    (project-specific)
  session-state.json (phase tracking)
```

**Hermes:**
```
~/.hermes/
  HERMES.md          (global rules, precedence absolute)
  HERMES.local.md    (project-specific fallback)

repo/
  .hermes/
    HERMES.local.md  (project-specific, preferred)
    session-state.json (phase tracking, gitignored)
```

### 4. `/magi:magi --ollama` → `/skill magi`

Claude's MAGI was a custom slash command wrapping `claude -p` sub-processes. Hermes MAGI is a proper skill using `execute_code` + direct HTTP.

**Claude:**
```bash
# MAGI spawns 3x `claude -p` processes
claude -p --model melchior-model ...
claude -p --model balthasar-model ...
claude -p --model caspar-model ...
```

**Hermes:**
```python
# Single asyncio event loop, 3x aiohttp POST calls
await asyncio.gather(
    post(endpoint, model="qwen3.1:latest", prompt=melchior_prompt),
    post(endpoint, model="llama3.2:latest", prompt=balthasar_prompt),
    post(endpoint, model="mistral:latest", prompt=caspar_prompt),
)
```

Faster, cleaner, no stdout parsing fragility.

### 5. Session State Management

**Claude:** `.claude/session-state.json` was read/written by hooks automatically.

**Hermes:** `./.hermes/session-state.json` must be read and written explicitly by the agent:

```python
import json
from pathlib import Path

STATE_PATH = Path(".hermes/session-state.json")

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"current_phase": "idle", "task_index": 0, "tasks": []}

def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))
```

The agent must call `load_state()` at the start of each turn and `save_state()` after each phase transition.

## Workflow Comparison

| Step | Claude | Hermes |
|------|--------|--------|
| 1. Read rules | Automatic (SessionStart hook) | Agent must read `~/.hermes/HERMES.md` then `./.hermes/HERMES.local.md` |
| 2. Write spec | Agent writes `.local.md` section | Agent writes `sbtdd/spec-behavior.md` |
| 3. Plan | `/writing-plans` slash command | `/skill plan` |
| 4. MAGI gate | `/magi:magi --ollama` | `/skill magi` (with spec+plan as payload) |
| 5. Execute TDD | Automatic phase enforcement via hooks | User declares phase (`TDD-Red:`, `TDD-Green:`, `TDD-Refactor:`) |
| 6. Verify | Automatic (hook runs on write) | Agent runs §0.1 commands explicitly |
| 7. Commit | Hook appends prefix | Agent formats message with prefix, user commits |
| 8. Pre-merge | Automatic dual-loop | Agent invokes review skills explicitly |

## Hermes Advantages

1. **Transparency**: Every enforcement action is visible in the conversation. Nothing happens behind the scenes.
2. **Portability**: Works on any platform Hermes supports (Terminal, Telegram, Discord, Slack, etc.).
3. **Model freedom**: MAGI uses any Ollama/vLLM/LMStudio model, not just Anthropic.
4. **Community extensibility**: Anyone can install, modify, or fork the skill.

## Hermes Disadvantages

1. **Manual enforcement**: Both agent and user must cooperate. A distracted agent or impatient user can break the protocol.
2. **No automatic verification**: The agent must remember to run §0.1 checks. There is no safety net.
3. **State file fragility**: If the agent crashes or the session ends abruptly, state may drift from reality.
4. **Learning curve**: Users must learn the `TDD-*:` prefixes. Claude's hooks were invisible.

## Recommendations

### For Users

1. **Always start with `TDD-Red:`**. This sets the protocol expectation for the session.
2. **Do not rush to Green**. The value of SBTDD is in the test design. A weak Red phase produces weak assurance.
3. **Run `/skill magi` before approving your own plans**. Self-review is unreliable.
4. **Check `.hermes/session-state.json` occasionally**. Ensure it matches your understanding.

### For Agent Authors

1. **Read HERMES.md first, always**. Even if the user seems impatient.
2. **Refuse phase violations explicitly**. Explain why, offer the correct prefix.
3. **Save state after every phase transition**. Not just at the end of the turn.
4. **Run §0.1 before every commit**. Not after, before.
5. **Escalate deviation**. If the user insists on skipping a gate, get explicit acknowledgment.

## Migration Path

If you have an existing Claude SBTDD project:

1. Copy `.claude/CLAUDE.md` to `~/.hermes/HERMES.md`.
2. Copy `.claude/CLAUDE.local.md` to `./.hermes/HERMES.local.md` (or `~/.hermes/HERMES.local.md`).
3. Convert `.claude/session-state.json` to `./.hermes/session-state.json`.
4. Remove any `.claude/` directory from the repo.
5. Add `.hermes/session-state.json` to `.gitignore`.
6. Install `/skill sbtdd` and `/skill magi`.
7. Start your next feature with `TDD-Red:`.

## References

- Hermes Agent docs: https://hermes-agent.nousresearch.com/docs
- MAGI skill: see `skills/magi/SKILL.md`
- Original Claude methodology: `.local.md` superpowers ecosystem
