# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-06-23
"""SBTDD Backend Client — OpenAI-compatible API calls for automated phases.

Mirrors MAGI's _http_post pattern but simplified for single-agent generation.
Posts to /chat/completions with a phase-specific prompt, receives markdown,
and writes it to disk.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sbtdd_hermes.backend_config import resolve_backend_config, get_model_for_phase

DEFAULT_TIMEOUT = 300


class BackendError(Exception):
    """Raised when the OpenAI-compatible backend returns an error."""


class BackendUnavailableError(Exception):
    """Raised when the backend is unreachable."""


def _http_post(
    host: str,
    body: dict[str, Any],
    timeout: int,
    api_key: str | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/chat/completions",
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace") if exc.fp else ""
        raise BackendError(f"HTTP {exc.code}: {exc.reason} — {detail}") from exc
    except (TimeoutError, OSError) as exc:
        raise BackendUnavailableError(f"Cannot reach backend at {host}: {exc}") from exc
    except urllib.error.URLError as exc:
        raise BackendUnavailableError(f"Cannot reach backend at {host}: {exc.reason}") from exc

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BackendError(f"Non-JSON response: {exc}") from exc

    if "choices" not in envelope or not envelope["choices"]:
        raise BackendError(f"Unexpected response shape: {list(envelope.keys())}")

    return envelope["choices"][0]["message"]


def _build_system_prompt(phase: str) -> str:
    """Return a system prompt appropriate for the SBTDD phase."""
    prompts = {
        "brainstorm": (
            "You are a senior software architect specializing in Behavior-Driven "
            "Development (BDD) and specification writing.\n\n"
            "Your task: read a base specification and write a refined, complete "
            "spec-behavior.md with these sections:\n"
            "1. Objective — one-sentence feature description\n"
            "2. Requirements (SDD) — numbered SHALL statements, traceable to scenarios\n"
            "3. Scenarios (BDD) — Given/When/Then blocks, one per behavior\n"
            "4. Constraints — measurable limits\n"
            "5. Non-goals — explicitly out of scope\n\n"
            "Rules:\n"
            "- BDD scenarios must be atomic (one scenario per behavior)\n"
            "- Every requirement MUST be traceable to at least one scenario\n"
            "- Constraints MUST be measurable (e.g., '< 200 ms', not 'fast')\n"
            "- NO template markers (\u003cfeature-name\u003e, \u003c!-- replace:)\n"
            "- Output ONLY the spec content, no markdown fences, no extra commentary\n"
            "- Preserve the language and domain of the original spec"
        ),
        "planning": (
            "You are a senior technical project manager specializing in TDD planning.\n\n"
            "Your task: read a spec-behavior.md and generate a structured TDD plan "
            "with tasks ordered as Red → Green → Refactor cycles.\n\n"
            "Output format: numbered tasks with acceptance criteria."
        ),
        "red": (
            "You are a test-driven developer writing failing tests.\n\n"
            "Your task: write minimal test code that will fail until the feature "
            "is implemented. Follow Arrange-Act-Assert pattern."
        ),
        "green": (
            "You are a test-driven developer writing production code.\n\n"
            "Your task: write the minimal production code needed to make the "
            "existing tests pass. No refactoring yet."
        ),
        "refactor": (
            "You are a senior software engineer focused on code quality.\n\n"
            "Your task: refactor existing code to improve readability, performance, "
            "and maintainability WITHOUT changing behavior. All existing tests must pass."
        ),
    }
    return prompts.get(phase, prompts["brainstorm"])


def _build_user_prompt(phase: str, content: str) -> str:
    """Wrap the input content with phase-specific instructions."""
    if phase == "brainstorm":
        return (
            f"Below is a base specification. Refine it into a complete spec-behavior.md:\n\n"
            f"---BASE SPEC---\n{content}\n---END SPEC---\n\n"
            f"Write the refined specification now."
        )
    elif phase == "planning":
        return (
            f"Below is a spec-behavior.md. Generate a TDD plan:\n\n"
            f"---SPEC---\n{content}\n---END SPEC---\n\n"
            f"Write the plan now."
        )
    else:
        return (
            f"Phase: {phase}\n\n"
            f"---INPUT---\n{content}\n---END INPUT---\n\n"
            f"Write the code/tests now."
        )


def _clean_response(text: str) -> str:
    """Strip markdown fences and extra whitespace from the LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:markdown)?\s*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
    return text


def generate_with_backend(
    phase: str,
    content: str,
    output_path: Path,
    *,
    host: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
    api_key: str | None = None,
) -> str:
    """Generate content via the backend and write it to disk.

    Args:
        phase: SBTDD phase (brainstorm, planning, red, green, refactor).
        content: The input content (e.g., spec-behavior-base.md).
        output_path: Where to write the generated content.
        host: OpenAI-compatible endpoint (default from config).
        model: Model identifier (default from config for the phase).
        timeout: Request timeout in seconds (default 300).
        api_key: Bearer token (default from SBTDD_BACKEND_API_KEY env var).

    Returns:
        Status message string for display to the user.

    Raises:
        BackendUnavailableError: If the backend is unreachable.
        BackendError: If the backend returns an error or invalid response.
    """
    cfg = resolve_backend_config()
    _host = host or cfg["base_url"]
    _model = model or get_model_for_phase(phase)
    _timeout = timeout or cfg.get("timeout", DEFAULT_TIMEOUT)
    _api_key = api_key or cfg.get("api_key")

    system_prompt = _build_system_prompt(phase)
    user_prompt = _build_user_prompt(phase, content)

    body = {
        "model": _model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.3,
    }

    print(f"[SBTDD Backend] Phase={phase}, model={_model}, timeout={_timeout}s", flush=True)

    try:
        message = _http_post(_host, body, _timeout, _api_key)
    except BackendUnavailableError as exc:
        raise BackendUnavailableError(
            f"Backend unreachable: {exc}. "
            f"Check that the backend is running at {_host} or set SBTDD_BACKEND_HOST."
        ) from exc

    raw_content = message.get("content", "")
    if not raw_content.strip():
        raise BackendError("Backend returned empty content.")

    cleaned = _clean_response(raw_content)

    # Write atomically (temp file + rename)
    tmp_path = output_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(cleaned, encoding="utf-8")
        tmp_path.rename(output_path)
    except OSError as exc:
        raise BackendError(f"Failed to write output: {exc}") from exc

    size = output_path.stat().st_size
    return (
        f"Generated {output_path.name} ({size} bytes) via {_model} at {_host}\n"
        f"Output: {output_path.absolute()}"
    )
