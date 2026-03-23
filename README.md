# Trine

A constraint-native balanced ternary computer. ALU, VM, and stored programs derived from first principles. Zero dependencies.

## What is this?

Trine is a complete ternary computational substrate — from trit primitives `{-1, 0, +1}` through an algebraically verified ALU through a programmable stack-based VM with three-way branching — built in pure Python with no external dependencies.

```python
from trine import TernaryMachine, TernaryVM, Instruction, Op

# Increment 13 in balanced ternary
m = TernaryMachine("increment").load_int(13).run()
assert m.to_int() == 14
print(m.balanced())  # "+---"

# Add two numbers via the ALU
m = TernaryMachine("add").load_two(13, 14).run()
assert m.to_int() == 27  # balanced ternary: "+000"

# Run a program: factorial(5) = 120
prog = [
    Instruction(Op.PUSH, 1),
    Instruction(Op.PUSH, 2), Instruction(Op.MUL),
    Instruction(Op.PUSH, 3), Instruction(Op.MUL),
    Instruction(Op.PUSH, 4), Instruction(Op.MUL),
    Instruction(Op.PUSH, 5), Instruction(Op.MUL),
    Instruction(Op.PRINT), Instruction(Op.HALT),
]
vm = TernaryVM(prog).run()
# → 120 (++++0)
```

## Architecture

```
Programs    →  factorial, fibonacci, loops, three-way branching
VM          →  stack machine, 20 opcodes, BR3 (ternary conditional)
ALU         →  add, sub, mul, inc, dec, neg, abs, shift, sign
Operations  →  injectable descriptors (the ONLY thing that changes)
FSM         →  MiniFSM tick cycle (read → classify → write → move)
Model       →  tape, head, carry register, trace
Primitives  →  Trit {-1, 0, +1}, sparse Tape, balanced ternary conversion
```

Each layer depends only on the one below it. The FSM never changes. Operations are injected as callables. The substrate is invariant.

## Why ternary?

- **No sign bit.** Every number is natively signed. No two's complement, no overflow asymmetry, no negative zero.
- **Negation is free.** Flip each trit. No carry propagation. O(1) per trit.
- **Three-way branching.** `BR3` dispatches on sign in one instruction. Binary needs two branches.
- **Multiplication is natively signed.** Shift-and-add with trit dispatch: POS = add, NEG = subtract, ZERO = skip. Booth recoding for free.
- **Neural network weights are ternary.** {-1, 0, +1} = excitatory, absent, inhibitory. The natural representation for AI inference.

## Algebraic proofs

The test suite verifies 161 cases including these algebraic properties:

| Property | Statement |
|----------|-----------|
| Symmetry | `inc(dec(n)) == n == dec(inc(n))` |
| Involution | `neg(neg(n)) == n` |
| Additive identity | `n + 0 == n` |
| Additive inverse | `n + (-n) == 0` |
| Commutativity | `a + b == b + a` |
| Inc equivalence | `inc(n) == n + 1` |
| Dec equivalence | `dec(n) == n + (-1)` |
| Shift inverse | `shr(shl(n)) == n` |
| Distributivity | `neg(a+b) == neg(a) + neg(b)` |
| Abs idempotent | `abs(abs(n)) == abs(n)` |

## VM instruction set

| Category | Instructions |
|----------|-------------|
| Stack | `PUSH` `DUP` `SWAP` `POP` `OVER` |
| Unary ALU | `INC` `DEC` `NEG` `ABS` `SHL` `SHR` `SGN` |
| Binary ALU | `ADD` `SUB` `MUL` |
| Control | `JMP` `JN` `JZ` `JP` `BR3` |
| I/O | `PRINT` `HALT` |

`BR3` is the ternary-native three-way branch: pop a value, jump to one of three targets based on sign (negative, zero, positive).

## Quick start

```bash
# Install
git clone https://github.com/digital-degenerates/trine.git
cd trine
pip install -e ".[test]"

# Run tests (161 cases, <1 second)
pytest

# Run demo
python -m trine.cli
```

Requires Python 3.10+. No external dependencies for the core library.

## Project status

**v0.1.0** — Software substrate complete. See [TRINE_SPEC.md](TRINE_SPEC.md) for the full roadmap from here through FPGA implementation, ternary neural network inference, and custom hardware.

## License

MIT — Dylan Griffin / Digital Degenerates
