"""
Scaffolding logic for /sbtdd-init.
Detects stack, renders templates, merges gitignore, creates directories.
"""

from pathlib import Path


STACK_MANIFESTS = {
    "rust": "Cargo.toml",
    "python": ("pyproject.toml", "setup.py", "requirements.txt"),
    "cpp": "CMakeLists.txt",
}

GITIGNORE_ENTRIES = [
    "/.hermes/",
    "/planning/",
    "/sbtdd/",
    "HERMES.local.md",
]


def detect_stack(root: Path) -> str | None:
    """Detect project stack by manifest files, searching upward from root."""
    current = root.resolve()
    while current != current.parent:
        for stack, manifests in STACK_MANIFESTS.items():
            if isinstance(manifests, str):
                manifests = (manifests,)
            for manifest in manifests:
                if (current / manifest).exists():
                    return stack
        current = current.parent
    return None


def render_hermes_local_md(stack: str | None, author: str | None = None, error_type: str | None = None, backend: str = "ollama") -> str:
    """Render HERMES.local.md template."""
    # TODO: Read from templates/HERMES.local.md.tmpl and substitute variables
    lines = [
        "# HERMES.local.md — SBTDD Project Rules",
        "",
        "## 0. Mandatory Code Standards",
        "- Read `~/.hermes/HERMES.md` first (absolute precedence)",
        "- §0.1 Per-phase verification (see stack section)",
        "- §0.2 Project-specific rules",
        "",
        "## 1. Methodology: SBTDD",
        "- Hierarchy: `sbtdd/spec-behavior-base.md` → `spec-behavior.md` → `planning/hermes-plan-tdd.md`",
        "- Tracking policy: `sbtdd/`, `planning/`, `.hermes/`, `HERMES.local.md` are NOT tracked by git",
        "",
        "## 2. Artefacts and State",
        "- Four sources of truth: HERMES.local.md, `.hermes/session-state.json`, git, plan",
        "- Canonical order: Git (past) > State (present) > Plan (future)",
        "",
    ]
    
    if stack:
        lines.extend([
            "## 4. Project Stack",
            f"- Language: {stack}",
            "- Test runner: see verification commands",
            "- TDD-Guard: implemented via native SBTDD plugin (`pre_tool_call` hook)",
            "",
        ])
    
    lines.extend([
        "## 5. Git Commit Conventions",
        "- `test:` → TDD-Red",
        "- `feat:`/`fix:` → TDD-Green",
        "- `refactor:` → TDD-Refactor",
        "- `chore:` → close task",
        "- English only, no AI refs, no Co-Authored-By, atomic commits",
        "",
    ])
    
    if error_type:
        lines.extend([
            "## 0.2 Error Handling",
            f"- Use `{error_type}` for domain errors",
            "",
        ])
    
    return "\n".join(lines)


def merge_gitignore(root: Path, entries: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Merge entries into .gitignore idempotently."""
    gitignore = root / ".gitignore"
    added: list[str] = []
    already_present: list[str] = []
    removed: list[str] = []
    
    existing = set()
    if gitignore.exists():
        with open(gitignore, "r", encoding="utf-8") as f:
            existing = set(line.strip() for line in f if line.strip() and not line.startswith("#"))
    
    new_entries = []
    for entry in entries:
        if entry in existing:
            already_present.append(entry)
        else:
            new_entries.append(entry)
            added.append(entry)
    
    if new_entries:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n")
            for entry in new_entries:
                f.write(f"{entry}\n")
    
    return added, already_present, removed


def create_directories(root: Path, dirs: list[str]) -> list[str]:
    """Create directories. Returns list of created dirs."""
    created = []
    for d in dirs:
        path = root / d
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


def seed_spec_behavior_base(root: Path) -> str:
    """Create spec-behavior-base.md template."""
    content = """# Spec-Behavior Base

## Problem Statement
(TODO: describe the problem this project solves)

## Core Behaviours

### Behaviour 1
**Given** ...  
**When** ...  
**Then** ...

### Behaviour 2
**Given** ...  
**When** ...  
**Then** ...

## Non-Functional Requirements
- Performance:
- Security:
- Reliability:

## Out of Scope
(TODO: explicitly state what is NOT in scope)
"""
    path = root / "sbtdd" / "spec-behavior-base.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


def scaffold_ollama_config(root: Path) -> str:
    """Placeholder for Ollama config scaffolding."""
    return "Ollama config scaffolding not yet implemented"
