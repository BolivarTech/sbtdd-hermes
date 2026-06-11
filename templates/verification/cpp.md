#### C/C++ (CMake)

```bash
cmake --build build --target all        # Compiles without warnings
ctest --test-dir build                  # All pass, 0 fail
```

If using Clang-Tidy:

```bash
clang-tidy -p build src/**/*.cpp        # 0 warnings
```
