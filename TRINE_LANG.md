# Trine High-Level Language Note

This document describes the current minimal high-level language compiled by
`src/trine/compiler.py`.

It is intentionally small and exists to prove the compiler pipeline, not to be
a complete language.

## Surface

- Functions: `fn name(arg1, arg2) { ... }`
- Integers: decimal literals
- Expressions:
  - variables
  - function calls
  - unary `-`
  - binary `+`, `-`, `*`, `/`, `%`
  - comparisons `==`, `!=`, `<`, `<=`, `>`, `>=`
- Statements:
  - `let name = expr;`
  - `name = expr;`
  - `if (expr) { ... } else { ... }`
  - `while (expr) { ... }`
  - `print expr;`
  - `return expr;`
  - `return;`
  - `expr;`

Example:

```text
fn fact(n) {
    if (n > 0) {
        return n * fact(n - 1);
    }
    return 1;
}

fn main() {
    print fact(5);
}
```

## Semantics

- `main` is required and must take zero parameters.
- Parameters are passed left-to-right and compiled against the current `CALL` / `RET` ABI.
- The compiler allocates function-scoped locals in memory-backed frames. `let`
  declarations are function-scoped and may not shadow parameters or other locals.
- Comparison expressions produce ordinary integers: `1` for true, `0` for false.
- Conditionals and loops treat `0` as false and any nonzero value as true.
- Compiled functions always return one integer value:
  - `return expr;` returns that value
  - `return;` returns `0`
  - falling off the end of a function returns `0`
- The return value of `main` is ignored by the VM entry stub.

## Current Limits

- No global variables or data declarations
- No strings or richer I/O
- No block-scoped locals or shadowing
- No indirect calls
- No logical `&&`, `||`, or `!`
- No chained comparisons

## Compiler API

- `compile_source(source)` -> assembly text
- `compile_file(path)` -> assembly text
- `compile_program(source)` -> `list[Instruction]`
- `compile_image(source)` -> `ProgramImage`
- `compile_file_program(path)` -> `list[Instruction]`
- `compile_file_image(path)` -> `ProgramImage`

You can also run the compiler module directly:

```bash
python -m trine.compiler examples/factorial_high_level.tri
python -m trine.compiler examples/factorial_high_level.tri --run
```
