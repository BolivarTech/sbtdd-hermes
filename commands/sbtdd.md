---
description: >
  Drive or resume the SBTDD workflow — routes by project state to the next phase.
  Invoke when the user mentions SBTDD, spec-driven development, or when
  initializing the workflow on a Hermes project.
---

Use the `sbtdd` skill (via the Skill tool) to inspect the current project state
(`sbtdd/`, `planning/`, `.hermes/session-state.json`) and execute the next SBTDD
phase.

## Flag: `--ollama`

`/sbtdd --ollama` runs or resumes the flow on the Ollama MAGI backend. The
backend is resolved by the presence of `./.hermes/magi-ollama.toml` (see
`review-gates.md §8` — MAGI Backend Selection); `--ollama` is the explicit,
**fail-closed** form: if that file does not exist, the orchestrator stops and
tells you to run `/sbtdd-init --ollama-init` first — it does not fall back to
the default backend silently. `/sbtdd` without the flag still uses Ollama when
the toml exists.
