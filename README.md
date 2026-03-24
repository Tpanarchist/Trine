# Trine

Trine is a pure-Python reference implementation of balanced ternary computation.
It models trits, a sparse tape, a constraint-separated ALU, a small
stored-program VM with a ternary-native three-way branch, and a line-oriented
assembler for the current VM ISA with constants, data directives, macros,
includes, a `ProgramImage` path for initialized memory, and explicit
subroutine control flow via `CALL` / `RET`.

The project is real in the sense that it computes correct balanced ternary
results and verifies algebraic properties of those operations. It is not native
ternary execution: the current system runs on binary hardware and uses Python to
simulate ternary semantics.

## What This Repo Proves

Trine currently demonstrates:

- Correct balanced ternary primitives and conversions
- A layered architecture with strict separation between constraints, model, and operations
- An extensible ALU surface built from injectable operation descriptors
- A clear split between primitive tape/FSM operations and composite helper operations
- `BR3` as a primitive ternary branch in the VM
- A runnable assembly-text path from `.trine` source to VM program, including labels, `DEF`, `ORG`, `DATA`, `INCLUDE`, and `MACRO`
- A `ProgramImage` path for initialized memory alongside the lowered instruction-list path
- A fuller stack-machine surface including `ROT`, `MIN`, `MAX`, `CONS`, `DIV`, and `MOD`
- Explicit `CALL` / `RET` with a separate return stack in the VM
- Include-based assembly library files for memory and frame management
- Memory-heavy and subroutine-focused assembly example programs
- A reproducible logical benchmark pass over operation and program metrics
- Algebraic and program-level correctness checks in an automated test suite

Trine does not currently demonstrate:

- Native ternary hardware
- Performance advantages over binary implementations
- A production inference runtime
- A hardware-ready machine and memory model

Ternary arithmetic is relevant to ternary-weight ML research, but this repo is
a software model, specification aid, and test oracle, not a performant
inference runtime.

## Example

```python
from trine import Instruction, Op, TernaryMachine, TernaryVM

# Increment 13 in balanced ternary
m = TernaryMachine("increment").load_int(13).run()
assert m.to_int() == 14
print(m.balanced())  # "+---"

# Add two numbers via the ALU
m = TernaryMachine("add").load_two(13, 14).run()
assert m.to_int() == 27  # balanced ternary: "+000"

# Run a VM program: factorial(5) = 120
prog = [
    Instruction(Op.PUSH, 1),
    Instruction(Op.PUSH, 2), Instruction(Op.MUL),
    Instruction(Op.PUSH, 3), Instruction(Op.MUL),
    Instruction(Op.PUSH, 4), Instruction(Op.MUL),
    Instruction(Op.PUSH, 5), Instruction(Op.MUL),
    Instruction(Op.PRINT), Instruction(Op.HALT),
]
vm = TernaryVM(prog).run()
# -> 120 (++++0)
```

See [`examples/factorial_vm.py`](examples/factorial_vm.py) for a runnable VM example,
[`examples/factorial.trine`](examples/factorial.trine) for raw assembly source,
[`examples/factorial_asm.py`](examples/factorial_asm.py) for an assembly-driven runner,
[`examples/count_to_five.trine`](examples/count_to_five.trine) for a label-based example,
[`examples/memory_examples.py`](examples/memory_examples.py) for the current
memory-heavy assembly programs in both lowered and image-backed modes,
[`examples/call_leaf.trine`](examples/call_leaf.trine) and
[`examples/factorial_call.trine`](examples/factorial_call.trine) for the current
subroutine examples, and [`examples/subroutine_examples.py`](examples/subroutine_examples.py)
for a list/image execution runner for those examples.

## Architecture

```
Programs          -> factorial, fibonacci, loops, branching, memory demos
Assembler         -> `.trine` text with labels, defs, data, includes, macros
Program Images    -> instructions plus initial memory
VM                -> stack machine, 33 opcodes, BR3, CALL/RET
Memory            -> LOAD, STORE, sparse default-zero word cells
Primitive ALU     -> increment, decrement, negate, add
Composite helpers -> abs, sub, cmp, min, max, cons, div, mod, mul, shift, sign
Operations        -> injectable descriptors
FSM               -> MiniFSM tick cycle
Model             -> tape, head, carry register, trace
Primitives        -> Trit, Tape, balanced ternary formatting/conversion
```

Each layer depends only on the one below it. The FSM enforces legal transitions.
The model performs the computation. Operations change behavior without changing
the substrate.

In the current codebase, only `increment`, `decrement`, `negate`, and `add`
execute as primitive tape/FSM operations. `abs`, `sub`, `cmp`, `min`, `max`,
`cons`, `div`, `mod`, `mul`, `shift_left`, `shift_right`, and `sign` are
composite helpers built either from those primitives or from direct host-side
logic. `DIV` truncates toward zero and `MOD` returns the paired remainder whose
sign follows the dividend. `LOAD` and `STORE` operate on sparse word-addressed
VM memory with default-zero reads and write-zero-deletes semantics. `CALL` and
`RET` are explicit composite control-flow operations over a separate VM return
stack. The assembler supports `DEF`, `INCLUDE`, `ORG`, `DATA`, and block
macros, can emit either a lowered instruction list or a `ProgramImage`, and
the stdlib now layers a hybrid frame convention over `CALL` / `RET` with
memory-backed locals in reserved negative address space.

## Why Ternary

- Balanced ternary is natively signed: no sign bit, no negative zero.
- Negation is a trit flip rather than a two's-complement transform.
- `BR3` is a natural ternary conditional, not a binary branch pattern adapted to ternary.
- Ternary values `{-1, 0, +1}` are relevant to quantized and ternary-weight ML research.

Those properties motivate the project. They do not, by themselves, prove that a
Python ternary simulator is faster or more useful than binary implementations.

## Verification

The test suite currently covers 316 cases across:

- Trit and tape primitives
- Balanced ternary conversion
- Unary and binary ALU behavior
- Composite operations
- Assembly parsing, directives, include handling, macro expansion, label resolution, image semantics, and execution
- Algebraic properties such as symmetry, involution, commutativity, and distributivity
- VM programs including loops, `BR3`, `CALL` / `RET`, frame macros, and memory-heavy assembly examples

The proofs establish semantic correctness of the implemented operations. They do
not establish hardware efficiency or application-level advantage.

For VM instrumentation, `alu_ticks` counts primitive `TernaryMachine` ticks and
`composite_ops` counts VM instructions implemented as host-side helpers or
compositions over primitive machine runs.

GitHub Actions CI runs `pytest -q` and a `python -m trine` smoke test on Python
3.10, 3.11, and 3.12.

## Quick Start

```bash
# Install
git clone https://github.com/digital-degenerates/trine.git
cd trine
python3.12 -m venv .venv312
.venv312/bin/python -m pip install -e ".[test]"

# Run tests
.venv312/bin/pytest

# Run the demo
.venv312/bin/python -m trine

# Run the example program
.venv312/bin/python examples/factorial_vm.py

# Run the assembly example
.venv312/bin/python examples/factorial_asm.py

# Run the label-based assembly example
.venv312/bin/python examples/count_to_five_asm.py

# Run the memory-heavy assembly examples in list and image modes
.venv312/bin/python examples/memory_examples.py

# Run the subroutine examples in list and image modes
.venv312/bin/python examples/subroutine_examples.py

# Run the benchmark note generator
.venv312/bin/python -m trine.benchmarks

# Or via the installed script entrypoint
.venv312/bin/trine-bench
```

Requires Python 3.10+. No external runtime dependencies are required for the core library.

On Windows, replace `python3.12` with `py -3.12` and use
`.venv312\Scripts\python` / `.venv312\Scripts\pytest`.

## Project Status

**v0.1.0**: the software reference stack is in place.

Current strengths:

- Clean layered package structure
- Extensible operation injection model
- Ternary-native `BR3`, explicit `CALL` / `RET`, `CMP`, `MIN`, `MAX`, `CONS`, `DIV`, `MOD`, `ROT`, and sparse word-addressed `LOAD`/`STORE`
- Executable assembler with labels, `DEF`, `ORG`, `DATA`, `INCLUDE`, block macros, `CALL` / `RET`, and `ProgramImage` output
- Include-based assembly stdlib with memory and frame macros plus memory-heavy and subroutine example programs
- Logical benchmark note covering `vm_steps`, `alu_ticks`, and `composite_ops`
- 316 passing tests
- CI and module entrypoint support

Current limits:

- Execution is still a Python simulation on binary hardware
- Performance is not competitive with native numeric libraries or hardware
- Several VM arithmetic instructions are still composite helpers, not single primitive tape/FSM ops
- The VM memory model is sparse host-side state, not a hardware-ready memory subsystem
- Call frames are currently a stdlib convention over sparse memory, not dedicated VM opcodes or a hardware-ready stack-frame mechanism
- The ISA is a Python-level interface, not a hardware-ready ternary encoding

See [BENCHMARKS.md](BENCHMARKS.md) for the current benchmark note,
[TRINE_SPEC.md](TRINE_SPEC.md) for the longer roadmap, and
[TRINE_ISA.md](TRINE_ISA.md) for the current instruction and assembly-text note.

## License

MIT - Dylan Griffin / Digital Degenerates
