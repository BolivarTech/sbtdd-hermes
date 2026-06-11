#### Rust

```bash
cargo nextest run                       # All pass, 0 fail
cargo clippy --all-targets -- -D warnings  # 0 warnings
cargo fmt --check                       # Clean
cargo build --release                   # Compiles without warnings
cargo doc --no-deps                     # No doc warnings
cargo audit                             # No known vulnerabilities
```
