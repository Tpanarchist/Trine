# Trine - Project Specification

**A constraint-native balanced ternary computer, currently implemented as a pure-Python reference model.**

Trine provides an ALU, VM, and stored-program examples derived from first
principles. The current system is a software specification and verification
artifact, not native ternary hardware and not a performance claim.

---

## Vision

Trine aims to describe what a balanced ternary computing stack could look like
from primitives through control flow and program execution.

Today, the project establishes two things:

- the semantics of the current ternary operations are correct as implemented
- the architecture is modular enough to extend without rewriting the whole substrate

It does **not** yet establish that ternary computation is faster, more
efficient, or commercially superior to binary approaches. Those questions only
become meaningful if later milestones validate the design in hardware or in
compiled implementations that remove Python interpreter overhead.

The long-term roadmap still includes FPGA work, ML-oriented experiments, and
possible hardware integration, but those remain contingent research directions,
not validated outcomes.

---

## What Trine Is

Trine is currently:

- a pure-Python reference implementation of balanced ternary semantics
- a specification aid for future HDL or lower-level implementations
- a test oracle for checking ternary behavior against algebraic properties
- a demonstration of a constraint-separated architecture with operation injection
- an executable assembler for the current line-oriented VM ISA text, including labels, directives, includes, and macros

Trine is not currently:

- native ternary execution
- a performant ML inference engine
- a hardware-ready ISA with fixed ternary instruction encoding
- a hardware-ready machine with rich memory and data structures

The distinction matters. Every current trit, ALU tick, and VM instruction is
executed by Python on conventional binary hardware.

---

## Architecture

Trine is layered. Each layer depends only on the layer below it.

```
Programs          -> factorial, fibonacci, loops, branching, memory demos
Compiler          -> minimal high-level language -> assembly text
Assembler         -> `.trine` text with labels, defs, data, includes, macros
Program Images    -> instructions plus initial memory
VM                -> stack, return stack, PC, opcodes, BR3, CALL/RET
Memory            -> LOAD, STORE, sparse default-zero word cells
Primitive ALU     -> increment, decrement, negate, add
Composite helpers -> abs, sub, cmp, min, max, cons, div, mod, mul, shifts, sign
Operations        -> injectable descriptors
FSM               -> MiniFSM tick cycle
Model             -> tape, head, carry, trace
Primitives        -> Trit, Tape, formatting, conversion
```

Only `increment`, `decrement`, `negate`, and `add` currently execute as
primitive tape/FSM operations. `abs`, `sub`, `cmp`, `min`, `max`, `cons`,
`div`, `mod`, `mul`, `shift_left`, `shift_right`, and `sign` are composite
helpers built either from those primitives or from direct host-side logic.
`DIV` truncates toward zero and `MOD` returns the paired remainder whose sign
follows the dividend. `LOAD` and `STORE` operate on sparse word-addressed VM
memory with default-zero reads and write-zero-deletes semantics. The assembler
can emit either a lowered instruction list or a `ProgramImage` that restores
initial memory on VM reset. `CALL` and `RET` are explicit composite
control-flow operations backed by a separate VM return stack, and the current
assembly stdlib layers a hybrid calling convention over them with
memory-backed locals in reserved negative address space. A minimal high-level
compiler now targets that same ABI and emits self-contained assembly text,
keeping the full pipeline inspectable from source language to VM execution.

### Core Principles

- **Constraint-native**: the FSM controls what transitions are legal; it does not compute values.
- **Model separation**: the model performs the work but does not define the transition graph.
- **Operation injection**: new ALU behavior is introduced by descriptors and rules, not by rewriting the substrate.
- **Algebraic verification**: properties such as symmetry, involution, and distributivity are encoded as executable tests.
- **Ternary-native control flow**: `BR3` is a primitive instruction rather than a binary branch idiom adapted to ternary.

This architecture is one of Trine's strongest proven contributions. It is a
structural property of the codebase, not a speculative future claim.

---

## Current Status (v0.1.0)

### What Exists

- Trit primitives: `Trit`, coercion, flip, formatting helpers
- Sparse default-zero tape
- Balanced ternary conversion with round-trip verification
- `MiniFSM` as the control substrate
- Injectable operation descriptors
- Primitive unary operations: increment, decrement, negate
- Primitive binary operation: addition with carry and second tape
- Stack rotation with `ROT`
- Composite helpers: abs, sign, shift-left, shift-right, subtraction, comparison, minimum, maximum, consensus, division, modulo, multiplication
- Sparse word-addressed VM memory with `LOAD` / `STORE`
- `TernaryVM` with 33 opcodes including `BR3`, `CALL`, and `RET`
- Assembler directives: `DEF`, `INCLUDE`, `ORG`, `DATA`, and block macros
- `ProgramImage` execution path with initialized memory and reset restoration
- Include-based assembly stdlib in `examples/lib/`
- Standard frame macros: `INIT_FRAMES`, `ENTER`, `LEAVE`, `LOCAL_LOAD`, `LOCAL_STORE`
- Minimal high-level language and compiler module
- `python -m trine` entrypoint and example VM program
- Runnable assembly example in `examples/factorial.trine`
- Runnable label-based assembly example in `examples/count_to_five.trine`
- Runnable memory-heavy assembly examples for array walking, linked-list traversal, and table-driven state machines
- Runnable subroutine examples for leaf calls and recursion
- Runnable compiled examples for recursion and loop-based locals
- Logical benchmark note in `BENCHMARKS.md`
- GitHub Actions CI running tests and a module smoke test
- 338 pytest cases covering primitives, operations, algebraic properties, memory, assembler directives/macros/includes, stack rotation, VM programs, benchmark harness behavior, subroutine control flow, compiler behavior, and memory-heavy examples
- VM metrics: `alu_ticks` for primitive machine ticks and `composite_ops` for host-side/composed VM instructions
- A small ISA / assembly-text note in `TRINE_ISA.md`

### What Is Proven

- The current operations produce correct results for the tested domains.
- The algebraic properties encoded in the suite hold for the implemented rules.
- The architecture supports extension without breaking the FSM/model separation.

### What Is Not Yet Proven

- Any performance advantage over binary implementations
- Suitability for serious ML workloads
- Faithful mapping of the full control path to FPGA or silicon
- Hardware-level efficiency, power, or throughput claims
- Commercial relevance beyond being a credible research/prototype artifact

### Current Limitations

- Execution is binary hardware simulating ternary semantics through Python.
- Correctness proofs do not imply speed, efficiency, or product readiness.
- Several VM instructions are composite host-side helpers rather than single primitive tape/FSM operations.
- The VM memory model is sparse host-side word storage, not a hardware-ready memory subsystem.
- The ISA is still a Python object interface rather than a ternary encoding.
- Call frames are currently a stdlib convention over sparse memory, not dedicated frame opcodes or a hardware-ready frame subsystem.
- The high-level language is intentionally narrow and does not yet include globals, strings, or richer data structures.
- The current control system relies on Python constructs that would need explicit HDL translation.

---

## Near-Term Priorities

1. Expand the high-level language beyond the current minimal core: globals/data, richer control, and better ergonomics.
2. Grow the assembly stdlib from memory/frame helpers toward more reusable program structure.
3. Continue validating the cost model with larger memory-heavy, subroutine-heavy, and compiler-generated programs.

---

## Milestones

The roadmap remains useful, but each stage depends on the earlier stages
actually validating the claims they are meant to test.

### M0: Foundation - complete

This milestone established the software reference stack.

- [x] Python package (`src/trine/`)
- [x] 301 pytest cases
- [x] Separated core library from CLI/demo code
- [x] README and project specification
- [x] `python -m trine` entrypoint
- [x] Example VM program
- [x] GitHub Actions CI

### M1: Robust ALU + VM - complete

**Goal**: Improve the software model so it is a stronger specification and test bed.

- [x] Memory-addressed load/store
- [x] Comparison operation (returns trit: less/equal/greater)
- [x] Small ISA specification document
- [x] Minimal assembly syntax specification
- [x] Integer division
- [x] Modular arithmetic
- [x] Ternary MIN / MAX / consensus operations
- [x] `ROT` instruction
- [x] Benchmarks focused on operation counts and ALU ticks, not marketing claims

### M2: Compiler + Assembler - complete

**Goal**: Make the VM easier to target while keeping its role as a reference machine.

- [x] Trine assembly language
- [x] Assembler: assembly text -> instruction list
- [x] Assembler ergonomics: constants, includes, data directives, block macros, and `ProgramImage`
- [x] Explicit subroutine ISA support with `CALL` / `RET`
- [x] Standard frame convention via assembly stdlib macros
- [x] Minimal high-level language
- [x] Compiler pipeline: high-level -> assembly -> VM program
- [x] Standard library in assembly

### M3: FPGA Proof of Concept

**Goal**: First real hardware validation of the architecture, if the translation holds up.

This is the first milestone that can test whether Trine maps beyond a Python
simulation. Success here would be meaningful. Failure here would also be
meaningful, because it would expose where the software model does not translate
cleanly to hardware.

- [ ] Full-adder truth table -> Verilog LUT
- [ ] 7-trit ripple-carry adder
- [ ] Ternary MAC building block
- [ ] Register file and control sequencer
- [ ] Verify all 27 full-adder cases against Python `rule_addition`
- [ ] Measure ops/sec, watts, and ops/watt before making stronger efficiency claims
- [ ] Target: Lattice iCE40-UP5K or ECP5

### M4: Ternary Neural Network Inference

**Goal**: Research whether the software model and any validated hardware can execute ternary-weight inference correctly.

This milestone is about correctness and benchmarking, not assuming competitive
performance in advance.

- [ ] Neuron forward pass as a VM or lower-level execution loop
- [ ] Load a published ternary-weight model or small benchmark network
- [ ] Run inference in Python and verify correctness
- [ ] If M3 succeeds, run the same workload on FPGA and verify identical results
- [ ] Benchmark latency, throughput, and energy before claiming advantage
- [ ] Compare against binary baselines with the expectation that Python Trine will be slower

### M5: Ternary-Native Training

**Goal**: Research whether ternary-native training ideas converge at all.

This is high-risk, high-information work. A negative result would still be
useful because it would narrow the commercial and technical thesis.

- [ ] Ternary forward pass
- [ ] Ternary backward/update rule
- [ ] Weight update as ternary state transition
- [ ] Small benchmark such as MNIST
- [ ] Convergence and accuracy study
- [ ] Compare against binary and quantized baselines
- [ ] Publish the result if it is technically interesting, positive or negative

### M6: Custom PCB

**Goal**: Build a physical platform only if earlier software and FPGA work justify it.

- [ ] PCB with FPGA(s) implementing a validated Trine execution core
- [ ] Host communication interface
- [ ] Visible trit indicators / debug surface
- [ ] Host-side driver and protocol
- [ ] Verify behavior against software and FPGA reference implementations

### M7: Product

**Goal**: Treat productization as aspirational and contingent, not assumed.

This stage only makes sense if earlier milestones show technical and economic
evidence that the architecture is worth turning into a product.

- [ ] Candidate runtime/backend integration
- [ ] Quantization tooling
- [ ] Hardware packaging and system integration
- [ ] Driver/runtime support
- [ ] Benchmark suite for throughput, latency, power, and cost
- [ ] Comparison against existing accelerators only after earlier validation succeeds

---

## Design Rationale

### Why Balanced Ternary

- No separate sign bit and no negative zero
- Negation as trit flip
- Naturally signed multiply/add behavior
- Native three-way comparison and branching
- Ternary values `{-1, 0, +1}` are relevant to quantized and ternary-weight ML research

These are architectural motivations. They are not proof that current software
execution is superior to binary implementations.

### Why Constraint-Native Separation

- The FSM never computes values
- The model never defines legal transition structure
- Operations can be added by descriptors and rules
- Violations tend to surface as explicit state/constraint problems
- The architecture scales conceptually better than a monolithic operation switchboard

### Why a Stack VM

- Operation arity maps cleanly to stack discipline
- `BR3` becomes a compact ternary-native control primitive
- The design is simpler to reason about than a register machine at this stage

That simplicity is useful for a reference machine, even though a future
hardware-targeted ISA may end up looking different.

### Why Zero Dependencies

- Easy to inspect
- Easy to run on constrained environments
- Easy to use as a readable specification artifact

The tradeoff is performance. Pure Python is excellent for clarity and poor for
making claims about efficient execution.

---

## Competitive Landscape

Trine does not exist in a vacuum.

- **SBTCVM** is real prior art in balanced ternary software. It demonstrates that vertical ternary software stacks existed before Trine.
- **Huawei** represents serious hardware-side work and serious timing risk. A large hardware organization can build a supporting software stack quickly once the hardware is ready.
- **Academic ternary ML work** shows that ternary-weight and quantized research is active, but that is different from having a reusable execution substrate.
- **Small hardware projects such as Triador** demonstrate that ternary hardware experimentation is real, even if scope and goals differ.

Trine's current differentiators are narrower and more defensible:

- derivation from first principles through a sequence of constrained architectural steps
- explicit separation of FSM constraints, model behavior, and operation descriptors
- algebraic verification encoded in tests
- `BR3` as a primitive ternary branch in the VM

Those are architectural properties visible in the repo today. Hardware
leadership, performance leadership, and product viability are not yet proven.

---

## Technical Risks

- **Performance risk**: Python overhead dominates execution cost. The current VM is not suitable for serious ML workloads.
- **Translation risk**: the control path must be re-expressed in HDL; Python dictionaries, callbacks, and dynamic binding do not carry over directly.
- **ISA maturity risk**: current instructions are Python-level objects, not ternary-encoded hardware instructions.
- **Memory-model gap**: sparse word-addressed memory exists now, but richer data structures and hardware mapping are still unresolved. Current call frames are a software convention over that memory model.
- **Training-risk**: ternary-native update rules may fail to converge or may underperform badly.
- **Hardware-risk**: FPGA implementations may not show efficiency gains even if semantic correctness is preserved.
- **Timing risk**: larger organizations, including Huawei or other hardware teams, may close the software gap quickly once they prioritize it.
- **Execution risk**: this remains a small, single-author project.

---

## Interpreting Future Claims

Stronger claims should only be made after the corresponding validation exists:

- **Semantic claims** are already supported by the current tests.
- **Performance claims** require compiled or hardware implementations plus benchmarks.
- **ML claims** require actual inference/training experiments.
- **Hardware claims** require FPGA or silicon behavior that matches the software model.
- **Commercial claims** require evidence beyond architectural cleanliness and novelty.

---

## License

MIT

---

## Author

Dylan Griffin - Digital Degenerates - Kentucky, USA

Built from first principles. Verified in software. Not yet validated in hardware.
