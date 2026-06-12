# Verification Commands — Rust Stack

## §0.1 Per-Phase Verification

```bash
# Format check
cargo fmt --check

# Linting
cargo clippy --all-targets --all-features -- -D warnings

# Build
cargo build

# Tests
cargo nextest run

# Documentation
cargo doc --no-deps

# Security audit
cargo audit
```

## Phase-specific notes

- **Red:** `cargo nextest run` should fail (tests written, no implementation)
- **Green:** `cargo nextest run` must pass (implementation added)
- **Refactor:** All checks above must pass; no `cargo audit` warnings
