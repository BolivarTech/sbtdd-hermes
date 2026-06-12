"""
Scaffolding logic for /sbtdd-init.
Detects stack, renders templates, merges gitignore, creates directories.
"""

from pathlib import Path

# Placeholder - will be filled in Task 4

def detect_stack(root: Path) -> str | None:
    if (root / "Cargo.toml").exists():
        return "rust"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "python"
    if (root / "CMakeLists.txt").exists():
        return "cpp"
    return None

def render_hermes_local_md(stack: str, author: str | None, error_type: str | None) -> str:
    return "# HERMES.local.md placeholder"

def merge_gitignore(root: Path, entries: list[str]) -> tuple[list, list, list]:
    gitignore = root / ".gitignore"
    added, already_present, removed = [], [], []
    # ... implementation ...
    return added, already_present, removed

def create_directories(root: Path, dirs: list[str]) -> list[str]:
    created = []
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        created.append(d)
    return created

def seed_spec_behavior_base(root: Path) -> str:
    return "spec-behavior-base.md placeholder"

def scaffold_ollama_config(root: Path) -> str:
    return "ollama config placeholder"
