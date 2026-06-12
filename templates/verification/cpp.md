# Verification Commands — C/C++ Stack

## §0.1 Per-Phase Verification

```bash
# Build
cmake --build build

# Tests
ctest --test-dir build --output-on-failure

# Static analysis (optional)
cppcheck --enable=all --error-exitcode=1 src/
```

## Phase-specific notes

- **Red:** `ctest` should fail (tests written, no implementation)
- **Green:** `ctest` must pass (implementation added)
- **Refactor:** All checks above must pass
