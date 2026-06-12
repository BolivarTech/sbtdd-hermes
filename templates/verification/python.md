# Verification Commands — Python Stack

## §0.1 Per-Phase Verification

```bash
# Format check
ruff format --check .

# Linting
ruff check .

# Type checking
mypy .

# Tests
pytest -v --tb=short

# Documentation (optional)
python -m doctest *.py
```

## Phase-specific notes

- **Red:** `pytest` should fail (tests written, no implementation)
- **Green:** `pytest` must pass (implementation added)
- **Refactor:** All checks above must pass
