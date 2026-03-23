# Trine ISA and Assembly Note

This document describes the current reference instruction set for `TernaryVM`
and the minimal assembly-text shape that maps onto it.

It is a software reference, not a ternary hardware encoding.

## Scope

- Stack values are signed Python integers.
- Memory is sparse, word-addressed, and default-zero.
- `PRINT` renders integers alongside balanced ternary formatting.
- Jumps may target raw numeric instruction indexes or labels.
- Primitive tape/FSM-executed arithmetic is limited to `INC`, `DEC`, `NEG`, and `ADD`.
- `ABS`, `SUB`, `CMP`, `MUL`, `SHL`, `SHR`, and `SGN` are composite helpers over the primitive substrate or host-side logic.

## Assembly Text

Current reference syntax is line-oriented:

```text
OPCODE [operand]
```

Rules:

- One instruction per line.
- Blank lines are ignored.
- `;` starts a comment.
- Labels use `name:` on their own line or before an instruction.
- Integer operands are decimal.
- `BR3` takes three comma-separated targets in `neg,zero,pos` order.
- The bundled assembler consumes this exact format today.
- Labels resolve to numeric instruction indexes during assembly.

Example:

```text
PUSH 4
PUSH 13
STORE
PUSH 4
LOAD
PRINT
HALT
```

Label example:

```text
PUSH 0
loop:
INC
DUP
PRINT
DUP
PUSH 5
SUB
JZ done
JMP loop
done:
HALT
```

## Machine State

- Stack: LIFO list of signed integers
- Memory: sparse map from integer address to integer value
- Program counter: zero-based instruction index
- Output: list of formatted strings written by `PRINT`

Memory rules:

- Reading an unwritten address yields `0`.
- Writing `0` deletes the cell from storage.
- Addresses may be any signed integer.

## Instruction Set

### Stack

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `PUSH` | int | `[] -> [value]` | Push literal integer |
| `DUP` | none | `[a] -> [a, a]` | Duplicate top value |
| `SWAP` | none | `[a, b] -> [b, a]` | Swap top two values |
| `POP` | none | `[a] -> []` | Discard top value |
| `OVER` | none | `[a, b] -> [a, b, a]` | Copy second item to top |

### Primitive ALU

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `INC` | none | `[a] -> [a + 1]` | Primitive machine op |
| `DEC` | none | `[a] -> [a - 1]` | Primitive machine op |
| `NEG` | none | `[a] -> [-a]` | Primitive machine op |
| `ADD` | none | `[a, b] -> [a + b]` | Primitive machine op |

### Composite Arithmetic

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `ABS` | none | `[a] -> [abs(a)]` | Composite helper |
| `SHL` | none | `[a] -> [a * 3]` | Balanced ternary shift-left |
| `SHR` | none | `[a] -> [trunc_toward_zero(a / 3)]` | Balanced ternary shift-right |
| `SGN` | none | `[a] -> [-1|0|+1]` | Sign as balanced trit |
| `SUB` | none | `[a, b] -> [a - b]` | Composite helper |
| `CMP` | none | `[a, b] -> [-1|0|+1]` | `-1` if `a < b`, `0` if equal, `+1` if `a > b` |
| `MUL` | none | `[a, b] -> [a * b]` | Composite helper |

### Memory

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `LOAD` | none | `[addr] -> [mem[addr]]` | Default-zero read |
| `STORE` | none | `[addr, value] -> []` | Writing zero deletes the cell |

### Control Flow

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `JMP` | pc | `[] -> []` | Unconditional jump |
| `JN` | pc | `[a] -> []` | Jump if `a < 0` |
| `JZ` | pc | `[a] -> []` | Jump if `a == 0` |
| `JP` | pc | `[a] -> []` | Jump if `a > 0` |
| `BR3` | `neg,zero,pos` | `[a] -> []` | Three-way branch on sign |

### I/O

| Opcode | Operand | Stack Effect | Notes |
| --- | --- | --- | --- |
| `PRINT` | none | `[a] -> []` | Appends formatted output |
| `HALT` | none | `[] -> []` | Stops execution |

## Notes for Future Assembler Work

- `BR3` should preserve `neg,zero,pos` target order.
- Data directives, constants, and macros are still future work.
- The current text form is intentionally minimal so the assembler can stay close to the existing VM.
