"""SBTDD-Hermes Plugin — root entry point for directory-based installation.

When installed as a directory plugin under ``~/.hermes/plugins/sbtdd/``,
Hermes imports this module and calls ``register(ctx)``. The actual
implementation lives in the ``sbtdd_hermes`` sub-package; this file simply
re-exports ``register``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure sbtdd_hermes is importable when loaded as a directory plugin.
# Hermes loads plugins via importlib with a custom loader; the plugin
# directory may not be in sys.path, breaking absolute imports.
_plugin_dir = Path(__file__).parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from sbtdd_hermes import register  # noqa: E402

__all__ = ["register"]
