"""Trine CLI — demo runner and interactive REPL."""

from __future__ import annotations

import sys
from pathlib import Path

from .assembler import assemble_file
from .formatting import format_trits, int_to_trits
from .machine import (
    TernaryMachine,
    ternary_abs,
    ternary_min,
    ternary_max,
    ternary_cons,
    ternary_div,
    ternary_mod,
)
from .operations import shift_left, shift_right, sign
from .vm import TernaryVM, Instruction, Op


def _bt(v: int) -> str:
    return format_trits(int_to_trits(v))


def _run(op: str, val: int) -> TernaryMachine:
    return TernaryMachine(op).load_int(val).run(max_steps=300)


def _run2(a: int, b: int) -> TernaryMachine:
    return TernaryMachine("add").load_two(a, b).run(max_steps=300)


def demo() -> None:
    sep = "-" * 58

    print("\n  -- INCREMENT --")
    for v, e in [(-5, -4), (-1, 0), (0, 1), (1, 2), (4, 5), (13, 14), (40, 41)]:
        r = _run("increment", v).to_int()
        print(f"    {'OK' if r == e else 'X '}  {v:>4d} ({_bt(v):>6s})  ->  {r:>4d} ({_bt(r):>6s})")

    print("\n  -- DECREMENT --")
    for v, e in [(5, 4), (1, 0), (0, -1), (-1, -2), (14, 13), (41, 40)]:
        r = _run("decrement", v).to_int()
        print(f"    {'OK' if r == e else 'X '}  {v:>4d} ({_bt(v):>6s})  ->  {r:>4d} ({_bt(r):>6s})")

    print("\n  -- NEGATE --")
    for v, e in [(1, -1), (-1, 1), (5, -5), (-13, 13), (0, 0), (40, -40)]:
        r = _run("negate", v).to_int()
        print(f"    {'OK' if r == e else 'X '}  {v:>4d} ({_bt(v):>6s})  ->  {r:>4d} ({_bt(r):>6s})")

    print("\n  -- ADDITION --")
    for (a, b), e in [((0, 0), 0), ((1, 1), 2), ((13, 14), 27), ((-13, 13), 0), ((40, 41), 81), ((100, 200), 300)]:
        r = _run2(a, b).to_int()
        print(f"    {'OK' if r == e else 'X '}  {a:>4d} + {b:>4d} = {r:>4d} ({_bt(r):>8s})")

    print(f"\n{sep}")
    print("  ALGEBRAIC PROOFS")
    print(sep)

    vals = [-40, -13, -1, 0, 1, 13, 40]

    print("\n  * Symmetry: inc(dec(n)) == n == dec(inc(n))")
    ok = all(
        _run("increment", _run("decrement", n).to_int()).to_int() == n ==
        _run("decrement", _run("increment", n).to_int()).to_int()
        for n in vals
    )
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  * Involution: neg(neg(n)) == n")
    ok = all(_run("negate", _run("negate", n).to_int()).to_int() == n for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  * Additive inverse: n + (-n) == 0")
    ok = all(_run2(n, _run("negate", n).to_int()).to_int() == 0 for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  * Commutativity: a + b == b + a")
    ok = all(_run2(a, b).to_int() == _run2(b, a).to_int() for a, b in [(1, 2), (13, -5), (-40, 27)])
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  * Equivalence: inc(n) == n + 1")
    ok = all(_run("increment", n).to_int() == _run2(n, 1).to_int() for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  * Distributivity: neg(a+b) == neg(a) + neg(b)")
    ok = all(
        _run("negate", _run2(a, b).to_int()).to_int() ==
        _run2(_run("negate", a).to_int(), _run("negate", b).to_int()).to_int()
        for a, b in [(1, 2), (13, -5), (-40, 27)]
    )
    print(f"    {'Passed' if ok else 'FAILED'}")

    print(f"\n{sep}")
    print("  VM PROGRAMS")
    print(sep)

    # Factorial(5) = 120
    print("\n  -- Factorial(5) = 120 --")
    prog = [
        Instruction(Op.PUSH, 1),
        Instruction(Op.PUSH, 2), Instruction(Op.MUL),
        Instruction(Op.PUSH, 3), Instruction(Op.MUL),
        Instruction(Op.PUSH, 4), Instruction(Op.MUL),
        Instruction(Op.PUSH, 5), Instruction(Op.MUL),
        Instruction(Op.PRINT), Instruction(Op.HALT),
    ]
    vm = TernaryVM(prog).run()
    for line in vm.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm.step_count}  alu_ticks={vm.alu_ticks}  "
        f"composite_ops={vm.composite_ops}"
    )

    # Memory round-trip
    print("\n  -- Memory round-trip: mem[4] = 13 --")
    prog_mem = [
        Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 13), Instruction(Op.STORE),
        Instruction(Op.PUSH, 4), Instruction(Op.LOAD),
        Instruction(Op.PRINT), Instruction(Op.HALT),
    ]
    vm_mem = TernaryVM(prog_mem).run()
    for line in vm_mem.output:
        print(f"    -> {line}")
    print(f"  memory={vm_mem.memory}")

    # Compare
    print("\n  -- Compare: cmp(2, 5) -> -1 --")
    prog_cmp = [
        Instruction(Op.PUSH, 2), Instruction(Op.PUSH, 5),
        Instruction(Op.CMP), Instruction(Op.PRINT), Instruction(Op.HALT),
    ]
    vm_cmp = TernaryVM(prog_cmp).run()
    for line in vm_cmp.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm_cmp.step_count}  alu_ticks={vm_cmp.alu_ticks}  "
        f"composite_ops={vm_cmp.composite_ops}"
    )

    # Composite min/max/consensus
    print("\n  -- Composite helpers: min(2, -5), max(2, -5), cons(4, 4), cons(4, -4) --")
    print(f"    -> min(2, -5) = {ternary_min(2, -5)}")
    print(f"    -> max(2, -5) = {ternary_max(2, -5)}")
    print(f"    -> cons(4, 4) = {ternary_cons(4, 4)}")
    print(f"    -> cons(4, -4) = {ternary_cons(4, -4)}")

    prog_minmax = [
        Instruction(Op.PUSH, 2), Instruction(Op.PUSH, -5),
        Instruction(Op.MIN), Instruction(Op.PRINT),
        Instruction(Op.PUSH, 2), Instruction(Op.PUSH, -5),
        Instruction(Op.MAX), Instruction(Op.PRINT),
        Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 4),
        Instruction(Op.CONS), Instruction(Op.PRINT),
        Instruction(Op.PUSH, 4), Instruction(Op.PUSH, -4),
        Instruction(Op.CONS), Instruction(Op.PRINT),
        Instruction(Op.HALT),
    ]
    vm_minmax = TernaryVM(prog_minmax).run()
    for line in vm_minmax.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm_minmax.step_count}  alu_ticks={vm_minmax.alu_ticks}  "
        f"composite_ops={vm_minmax.composite_ops}"
    )

    # Composite division/modulo
    print("\n  -- Composite helpers: div(-7, 3), mod(-7, 3) --")
    print(f"    -> div(-7, 3) = {ternary_div(-7, 3)}")
    print(f"    -> mod(-7, 3) = {ternary_mod(-7, 3)}")

    prog_divmod = [
        Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
        Instruction(Op.DIV), Instruction(Op.PRINT),
        Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
        Instruction(Op.MOD), Instruction(Op.PRINT),
        Instruction(Op.HALT),
    ]
    vm_divmod = TernaryVM(prog_divmod).run()
    for line in vm_divmod.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm_divmod.step_count}  alu_ticks={vm_divmod.alu_ticks}  "
        f"composite_ops={vm_divmod.composite_ops}"
    )

    # Stack rotation
    print("\n  -- Stack ROT: [1, 2, 3] -> [2, 3, 1] --")
    prog_rot = [
        Instruction(Op.PUSH, 1), Instruction(Op.PUSH, 2), Instruction(Op.PUSH, 3),
        Instruction(Op.ROT), Instruction(Op.HALT),
    ]
    vm_rot = TernaryVM(prog_rot).run()
    print(f"  stack={vm_rot.stack}")

    # Assembly example
    print("\n  -- Assembly: factorial.trine --")
    asm_program = assemble_file(Path(__file__).resolve().parents[2] / "examples" / "factorial.trine")
    vm_asm = TernaryVM(asm_program).run()
    for line in vm_asm.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm_asm.step_count}  alu_ticks={vm_asm.alu_ticks}  "
        f"composite_ops={vm_asm.composite_ops}"
    )

    # Label-based assembly example
    print("\n  -- Assembly with labels: count_to_five.trine --")
    asm_loop = assemble_file(Path(__file__).resolve().parents[2] / "examples" / "count_to_five.trine")
    vm_loop = TernaryVM(asm_loop).run()
    for line in vm_loop.output:
        print(f"    -> {line}")
    print(
        f"  vm_steps={vm_loop.step_count}  alu_ticks={vm_loop.alu_ticks}  "
        f"composite_ops={vm_loop.composite_ops}"
    )

    # Fibonacci
    print("\n  -- Fibonacci: first 8 terms --")
    prog_fib = [
        Instruction(Op.PUSH, 0), Instruction(Op.DUP), Instruction(Op.PRINT),
        Instruction(Op.PUSH, 1),
    ]
    for _ in range(7):
        prog_fib.extend([
            Instruction(Op.DUP), Instruction(Op.PRINT), Instruction(Op.SWAP),
            Instruction(Op.OVER), Instruction(Op.ADD),
        ])
    prog_fib.append(Instruction(Op.HALT))
    vm_fib = TernaryVM(prog_fib).run()
    for line in vm_fib.output:
        print(f"    -> {line}")
    actual = [int(o.split()[0]) for o in vm_fib.output]
    print(f"  {'OK' if actual == [0, 1, 1, 2, 3, 5, 8, 13] else 'X '} sequence correct")
    print(
        f"  vm_steps={vm_fib.step_count}  alu_ticks={vm_fib.alu_ticks}  "
        f"composite_ops={vm_fib.composite_ops}"
    )

    # Powers of 2
    print("\n  -- Powers of 2: 2^0..2^7 --")
    prog_pow = [
        Instruction(Op.PUSH, 1),
        Instruction(Op.DUP), Instruction(Op.PRINT),
    ]
    for _ in range(7):
        prog_pow.extend([
            Instruction(Op.DUP), Instruction(Op.ADD),
            Instruction(Op.DUP), Instruction(Op.PRINT),
        ])
    prog_pow.append(Instruction(Op.HALT))
    vm_pow = TernaryVM(prog_pow).run()
    for line in vm_pow.output:
        print(f"    -> {line}")
    actual = [int(o.split()[0]) for o in vm_pow.output]
    print(f"  {'OK' if actual == [2**i for i in range(8)] else 'X '} sequence correct")
    print(
        f"  vm_steps={vm_pow.step_count}  alu_ticks={vm_pow.alu_ticks}  "
        f"composite_ops={vm_pow.composite_ops}"
    )


def main() -> int:
    print("\n  Trine - constraint-native balanced ternary computer\n")
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
