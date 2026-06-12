"""SBTDD-Hermes Plugin — root entry point for directory-based installation.

When installed as a directory plugin under ``~/.hermes/plugins/sbtdd/``,
Hermes imports this module and calls ``register(ctx)``. The actual
implementation lives in the ``sbtdd_hermes`` sub-package; this file simply
re-exports ``register``.
"""

from __future__ import annotations

from sbtdd_hermes import register

__all__ = ["register"]
