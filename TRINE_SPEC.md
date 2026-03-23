# Trine — Project Specification

**A constraint-native balanced ternary computer.**

ALU, VM, and stored programs derived from first principles. Zero dependencies.

---

## Vision

Trine is a complete ternary computational substrate — from trit primitives through
an algebraically verified ALU through a programmable VM — designed as the
software foundation for ternary AI inference and training hardware.

The long-term goal is a ternary computing platform that spans software, FPGA,
and custom silicon, targeting AI workloads where balanced ternary arithmetic
provides structural advantages over binary: signed multiply-accumulate,
three-way branching, and memory-efficient weight representation.

---

## Architecture

Trine is layered. Each layer depends only on the one below it. The FSM
substrate never changes. Only the parameterization changes.

```
┌─────────────────────────────────────────────┐
│  Programs    (factorial, fibonacci, etc.)    │
├─────────────────────────────────────────────┤
│  VM          (stack, PC, opcodes, BR3)      │
├─────────────────────────────────────────────┤
│  ALU         (add, sub, mul, neg, abs, etc.)│
├─────────────────────────────────────────────┤
│  Operations  (injectable descriptors)       │
├─────────────────────────────────────────────┤
│  FSM         (MiniFSM — tick cycle)         │
├─────────────────────────────────────────────┤
│  Model       (tape, head, carry, trace)     │
├─────────────────────────────────────────────┤
│  Primitives  (Trit, Tape, formatting)       │
└─────────────────────────────────────────────┘
```

### Core Principles

- **Constraint-native**: The FSM controls what is *permitted*. The model
  controls what *happens*. They never leak into each other.
- **Operation injection**: Every ALU operation is a callable descriptor.
  The substrate is invariant; only the classification rule changes.
- **Algebraically verified**: Operations are proven correct via compositional
  tests — symmetry, involution, identity, commutativity, distributivity.
- **Three-way branching**: `BR3` is a primitive instruction, not a
  composition of two binary branches. This is native ternary control flow.
- **Zero dependencies**: The entire system runs in pure Python with no
  external packages. Portable to any Python 3.10+ environment.

---

## Current Status (v0.1.0)

### What exists

- **Trit primitives**: `Trit` enum ({-1, 0, +1}), coercion, flip, formatting
- **Sparse tape**: default-zero, unbounded, write-ZERO-deletes invariant
- **Balanced ternary conversion**: `int_to_trits`, `trits_to_int`, round-trip verified
- **MiniFSM**: pure-Python FSM with hierarchical dot-separated state names,
  `on_enter` callbacks, wildcard sources, before/after hooks
- **Operation descriptors**: `OpDescriptor(name, rule, halt_check, uses_carry, binary)`
- **Unary operations**: increment, decrement, negate (FSM-driven); abs, sign,
  shift_left, shift_right (composite/tape)
- **Binary operations**: addition with carry register and second tape
- **Multiplication**: shift-and-add via trit dispatch (natively signed, Booth-free)
- **Subtraction**: add(a, negate(b)) composition
- **TernaryVM**: stack-based VM with 20 opcodes including `BR3` (three-way branch),
  `OVER`, `MUL`, `SUB`, stored programs with loops and conditional branching
- **161 pytest cases** covering primitives, operations, algebraic proofs, and
  VM programs — all passing in under 1 second

### What does not exist yet

- FPGA implementation
- Neural network inference or training
- Hardware design files
- Compiler or assembler toolchain
- GitHub Actions CI

---

## Milestones

### M0: Foundation ✓

Clean repo with proper package structure, tests, documentation.

- [x] Python package (`src/trine/`)
- [x] 161 parametrized pytest cases
- [x] Separated core library from CLI demo
- [x] README with architecture overview and examples
- [x] MIT LICENSE
- [x] Push to GitHub

### M1: Robust ALU + VM

**Goal**: Production-quality instruction set with full test coverage.

- [ ] Comparison operation (returns trit: less/equal/greater)
- [ ] Integer division (repeated subtraction or shift-and-subtract)
- [ ] Modular arithmetic
- [ ] Bitwise ternary operations (MIN, MAX, consensus)
- [ ] `ROT` instruction (rotate top 3 stack elements)
- [ ] Memory-addressed load/store (move beyond pure stack)
- [ ] Formal ISA specification document
- [ ] Benchmarks: operation counts and ALU ticks for standard algorithms
- [ ] GitHub Actions CI (pytest on Python 3.10, 3.11, 3.12)

### M2: Compiler + Assembler

**Goal**: Write programs in a higher-level format, compile to Trine VM.

- [ ] Trine assembly language (human-readable mnemonics, labels, immediates)
- [ ] Assembler: assembly text → instruction list
- [ ] Minimal high-level language (Forth-like or C-subset)
- [ ] Compiler: high-level → assembly → bytecode
- [ ] Standard library in Trine assembly

### M3: FPGA Proof of Concept

**Goal**: Ternary ALU on physical hardware, verified against software.

- [ ] Full adder truth table → Verilog LUT
- [ ] 7-trit ripple-carry adder
- [ ] Ternary MAC unit (sign-select mux + adder)
- [ ] MAC array for parallel inference
- [ ] Register file and control sequencer
- [ ] Verify all 27 full-adder cases against Python `rule_addition`
- [ ] Benchmark: ops/sec, watts, ops/watt
- [ ] Target: Lattice iCE40-UP5K or ECP5

### M4: Ternary Neural Network Inference

**Goal**: Run a pre-trained ternary-quantized model on Trine.

- [ ] Neuron forward pass as VM program (ternary MAC loop)
- [ ] Load published ternary weight matrix (ternary ResNet or BERT on MNIST)
- [ ] Run inference in Python, verify accuracy
- [ ] Run inference on FPGA, verify identical results
- [ ] Benchmark: accuracy, latency, energy per inference
- [ ] Compare against binary CPU/GPU inference

### M5: Ternary-Native Training

**Goal**: Train a neural network from scratch using ternary arithmetic only.

- [ ] Ternary forward pass (MAC with {-1, 0, +1} weights)
- [ ] Ternary backward pass (sign propagation, not gradient descent)
- [ ] Weight update as ternary state transition (counter + threshold)
- [ ] Train on MNIST from random ternary initialization
- [ ] Accuracy convergence curve
- [ ] Compare against full-precision SGD, post-training quantization, binary NN
- [ ] Technical report / arxiv preprint

### M6: Custom PCB

**Goal**: Physical ternary computer on a PCB.

- [ ] PCB with FPGA(s) implementing Trine ISA
- [ ] Standard interface (USB/UART for host communication)
- [ ] LED trit indicators
- [ ] Host-side driver and protocol
- [ ] Verify against software and FPGA prototypes
- [ ] Optional: PCIe version for server integration

### M7: Product

**Goal**: Ternary AI inference accelerator for existing systems.

- [ ] PyTorch custom backend (`torch.device('trine')`)
- [ ] Automatic ternary quantization of trained models
- [ ] PCIe card with DMA controller
- [ ] Linux kernel driver
- [ ] Benchmark suite: latency, throughput, power, cost per inference
- [ ] Compare against NVIDIA T4, Google Coral, Intel Movidius

---

## Design Decisions

### Why balanced ternary?

- Symmetric representation: no sign bit, no two's complement, no negative zero
- Negation is trit-flip (O(1) per trit, no carry propagation)
- Multiplication is natively signed (Booth recoding is free)
- Three-way comparison is primitive (less/equal/greater in one operation)
- Neural network weights are naturally {-1, 0, +1}
- Information density: 1 trit = 1.585 bits per wire

### Why constraint-native architecture?

- The FSM never computes — it only permits legal transitions
- Operations are injected as descriptors, not hardcoded
- The substrate is invariant across all operations
- Bugs manifest as constraint violations, not silent corruption
- Every operation is independently verifiable via algebraic proofs

### Why a stack-based VM?

- Operation arity maps naturally to stack discipline
- Zero-address instruction format minimizes instruction size
- Three-way branch (`BR3`) is one instruction, one pop, three targets
- Simpler than register machines to implement in hardware

### Why zero dependencies?

- Portability: runs on Pydroid (Android), CPython, PyPy, anywhere
- Auditability: the entire system is readable top to bottom
- Reproducibility: no version conflicts, no install failures
- The code IS the specification

---

## Competitive Landscape

| Entity | What they have | What they lack |
|--------|---------------|----------------|
| Huawei | Gate-level patent (CN119652311A), CNTFET research | ISA, software stack, commercial chip |
| SBTCVM | 9-trit balanced ternary VM with compilers | Algebraic verification, AI focus, hardware path |
| Triador | 3-trit hardware computer (DG403 switches) | Programmability, scale, AI application |
| Academic papers | Ternary neural network quantization research | Execution substrate, hardware, native training |
| **Trine** | **Complete verified software stack, ISA, VM, programs** | **FPGA implementation, training results, hardware** |

The gap Trine fills: the architecture layer between gate-level hardware and
application-level AI, with a verified software stack that serves as both
prototype and formal specification.

---

## Technical Risks

- **Ternary-native training convergence**: No guarantee that discrete ternary
  weight updates converge as well as continuous gradient descent. Mitigated by
  existing sign-SGD convergence proofs and Hebbian learning theory.
- **FPGA performance**: Ternary operations encoded in binary LUTs may not
  achieve predicted efficiency gains. Mitigated by benchmarking early (M3).
- **Market timing**: Huawei or others may build a competing software stack.
  Mitigated by publishing early and establishing prior art.
- **Single-person execution risk**: Currently a one-person project.
  Mitigated by clean architecture, comprehensive tests, and open source.

---

## License

MIT

---

## Author

Dylan Griffin · Digital Degenerates · Kentucky, USA

Built from first principles. Proven algebraically. Runs on a phone.
