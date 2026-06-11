from pathlib import Path

# Project root: the directory where pyproject.toml lives.
ROOT = Path(__file__).parent.parent


def frontmatter(text: str) -> str:
    """Return only the YAML frontmatter block (between --- fences) from *text*.
    If no frontmatter is present, return the empty string."""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[1].strip()
