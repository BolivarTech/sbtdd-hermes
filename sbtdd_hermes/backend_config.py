# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-06-23
"""SBTDD Backend Configuration — layered TOML + env resolution.

Mirrors the MAGI Ollama config pattern but adapted for SBTDD per-phase
model selection.
"""

from __future__ import annotations

import os
import sys
import tomllib
from typing import Any, Mapping

DEFAULT_BASE_URL = "http://localhost:11434/v1"

#: Default per-phase models (local-friendly defaults).
DEFAULT_PHASES: Mapping[str, str] = {
    "brainstorm": "deepseek-v4-pro:cloud",
    "planning": "qwen3.5:397b-cloud",
    "red": "kimi-k2.7-code:cloud",
    "green": "kimi-k2.7-code:cloud",
    "refactor": "kimi-k2.7-code:cloud",
}

_KNOWN_TOP_KEYS = {"base_url", "api_key", "phases", "timeout"}


def _normalize_base_url(raw: str) -> str:
    raw = raw.rstrip("/")
    if "://" not in raw:
        raw = f"http://{raw}"
    tail = raw.split("://", 1)[1]
    if "/" not in tail:
        raw = f"{raw}/v1"
    return raw


def _load_toml(path: str) -> dict[str, Any]:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        print(f"WARNING: malformed TOML at {path}: {exc}", file=sys.stderr)
        return {}
    for key in set(data) - _KNOWN_TOP_KEYS:
        print(f"WARNING: unknown key '{key}' in {path} (ignored)", file=sys.stderr)
    return data


def resolve_backend_config(
    *,
    global_path: str | None = None,
    repo_path: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve backend config from defaults + global/repo TOML + env.

    Precedence per key (high → low):
    1. SBTDD-specific env vars (SBTDD_BACKEND_*).
    2. Repo-level TOML (.hermes/sbtdd.toml).
    3. Global TOML (~/.hermes/sbtdd.toml).
    4. Built-in defaults.

    SECURITY: api_key is NEVER read from TOML. Only from
    SBTDD_BACKEND_API_KEY env var (or empty for no-auth).
    """
    if env is None:
        env = os.environ
    if global_path is None:
        global_path = os.path.expanduser("~/.hermes/sbtdd.toml")
    if repo_path is None:
        repo_path = os.path.join(os.getcwd(), ".hermes", "sbtdd.toml")

    g = _load_toml(global_path)
    r = _load_toml(repo_path)

    # base_url
    if env.get("SBTDD_BACKEND_HOST"):
        raw_host = env["SBTDD_BACKEND_HOST"]
    elif r.get("base_url"):
        raw_host = r["base_url"]
    elif g.get("base_url"):
        raw_host = g["base_url"]
    else:
        raw_host = DEFAULT_BASE_URL
    base_url = _normalize_base_url(raw_host)

    # api_key: ONLY from env var, never from TOML (security)
    api_key = env.get("SBTDD_BACKEND_API_KEY") or None

    # timeout (seconds)
    timeout = (
        env.get("SBTDD_BACKEND_TIMEOUT")
        or r.get("timeout")
        or g.get("timeout")
        or "300"
    )
    try:
        timeout_int = int(timeout)
    except ValueError:
        timeout_int = 300

    # phases per phase name
    g_phases = g.get("phases", {}) or {}
    r_phases = r.get("phases", {}) or {}
    phases: dict[str, str] = {}
    for phase in DEFAULT_PHASES:
        ekey = f"SBTDD_BACKEND_MODEL_{phase.upper()}"
        if env.get(ekey):
            phases[phase] = env[ekey]
        elif r_phases.get(phase):
            phases[phase] = r_phases[phase]
        elif g_phases.get(phase):
            phases[phase] = g_phases[phase]
        else:
            phases[phase] = DEFAULT_PHASES[phase]

    return {
        "base_url": base_url,
        "api_key": api_key,
        "phases": phases,
        "timeout": timeout_int,
    }


def get_model_for_phase(phase: str) -> str:
    """Return the model identifier for a given SBTDD phase."""
    cfg = resolve_backend_config()
    return cfg["phases"].get(phase, DEFAULT_PHASES.get(phase, "qwen2.5-coder:32b"))


def get_backend_host() -> str:
    """Return the resolved backend base URL."""
    return resolve_backend_config()["base_url"]


def get_backend_api_key() -> str | None:
    """Return the API key from env, or None."""
    return os.environ.get("SBTDD_BACKEND_API_KEY") or None
