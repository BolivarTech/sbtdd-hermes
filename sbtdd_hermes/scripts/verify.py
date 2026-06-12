"""
Executes verification commands for a given stack.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Any

SCRIPT_TIMEOUT = 60


def run_with_error_handling(cmd: list[str], timeout: int = SCRIPT_TIMEOUT) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return False, f"Exit code {result.returncode}: {result.stderr}"
        return True, result.stdout
    except FileNotFoundError as e:
        return False, f"Tool not found: {e}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def run_verification(stack: str, check_only: bool = False) -> dict[str, Any]:
    """Run verification commands for the given stack."""
    commands = _get_commands(stack)
    results: list[dict[str, str]] = []
    all_passed = True

    for name, cmd in commands:
        if check_only:
            # Just check if tool exists
            ok, msg = run_with_error_handling([cmd[0], "--version"], timeout=5)
            results.append({"name": name, "status": "available" if ok else "missing", "detail": msg})
            if not ok:
                all_passed = False
        else:
            ok, msg = run_with_error_handling(cmd)
            results.append({"name": name, "status": "PASSED" if ok else "FAILED", "detail": msg})
            if not ok:
                all_passed = False

    return {"stack": stack, "all_passed": all_passed, "results": results}


def _get_commands(stack: str) -> list[tuple[str, list[str]]]:
    """Return verification commands for stack."""
    base = Path(__file__).parent.parent.parent / "templates" / "verification"

    # Try to load from template file
    template_file = base / f"{stack}.md"
    if template_file.exists():
        return _parse_commands_from_file(template_file)

    # Default commands
    defaults = {
        "rust": [
            ("cargo fmt --check", ["cargo", "fmt", "--check"]),
            ("cargo clippy", ["cargo", "clippy", "--all-targets", "--all-features", "--", "-D", "warnings"]),
            ("cargo build", ["cargo", "build"]),
            ("cargo nextest run", ["cargo", "nextest", "run"]),
            ("cargo doc", ["cargo", "doc", "--no-deps"]),
        ],
        "python": [
            ("ruff format --check", ["ruff", "format", "--check", "."]),
            ("ruff check", ["ruff", "check", "."]),
            ("mypy", ["mypy", "."]),
            ("pytest", ["pytest", "-v", "--tb=short"]),
        ],
        "cpp": [
            ("cmake build", ["cmake", "--build", "build"]),
            ("ctest", ["ctest", "--test-dir", "build", "--output-on-failure"]),
        ],
    }
    return defaults.get(stack, [])


def _parse_commands_from_file(path: Path) -> list[tuple[str, list[str]]]:
    """Parse verification commands from markdown template."""
    commands: list[tuple[str, list[str]]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if line.startswith("```"):
                continue
            # Simple parsing: each line is a command
            parts = line.split()
            if parts:
                commands.append((line, parts))
    return commands


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="SBTDD Verification Runner")
    parser.add_argument("--stack", default="python", choices=["rust", "python", "cpp"])
    parser.add_argument("--check-only", action="store_true", help="Check tool availability only")
    args = parser.parse_args()

    result = run_verification(args.stack, check_only=args.check_only)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
