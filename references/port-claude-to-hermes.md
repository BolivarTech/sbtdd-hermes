# Migration: Claude Skill → Hermes Plugin

## Key Differences

| Feature | Claude Skill | Hermes Plugin |
|---------|-------------|---------------|
| Registration | `CLAUDE.md` + `settings.json` | `pyproject.toml` entry-point |
| Commands | Superpowers `/sbtdd` | Slash commands `/sbtdd` |
| Tools | N/A | `sbtdd_status`, `sbtdd_update_state` |
| Hooks | `PreToolUse` | `pre_tool_call`, `on_session_start` |
| TDD-Guard | External binary | Native `pre_tool_call` hook |
| State | `.claude/state.json` | `.hermes/session-state.json` |
| MAGI | `/skill magi` | `/skill magi` (same) |

## API Dependencies

- Hermes tool names: `write_file`, `patch`, `terminal` (configurable in `_config.py`)
- Hooks: `pre_tool_call`, `on_session_start`
- Slash commands: `sbtdd`, `sbtdd-init`, `sbtdd-check`
- Tools: `sbtdd_status`, `sbtdd_update_state`

## Known Limitations

1. **Single session per directory:** Concurrent Hermes sessions on same project will contend for `session-state.json`
2. **Heuristic TDD-Guard:** ~85% accuracy; monitor false positives
3. **Windows multiprocessing:** Uses `spawn`; ensure module has no import-time side effects
4. **NFS filesystems:** Cache mtime may truncate to seconds; rare edge case
