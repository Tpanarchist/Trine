"""Trine CLI — demo runner and interactive REPL."""

from __future__ import annotations

import sys

from .formatting import format_trits, int_to_trits
from .machine import TernaryMachine, ternary_abs
from .operations import shift_left, shift_right, sign
from .vm import TernaryVM, Instruction, Op


def _bt(v: int) -> str:
    return format_trits(int_to_trits(v))


def _run(op: str, val: int) -> TernaryMachine:
    return TernaryMachine(op).load_int(val).run(max_steps=300)


def _run2(a: int, b: int) -> TernaryMachine:
    return TernaryMachine("add").load_two(a, b).run(max_steps=300)


def demo() -> None:
    SEP = "─" * 58

    print("\n  ── INCREMENT ──")
    for v, e in [(-5, -4), (-1, 0), (0, 1), (1, 2), (4, 5), (13, 14), (40, 41)]:
        r = _run("increment", v).to_int()
        print(f"    {'✓' if r == e else '✗'}  {v:>4d} ({_bt(v):>6s})  →  {r:>4d} ({_bt(r):>6s})")

    print("\n  ── DECREMENT ──")
    for v, e in [(5, 4), (1, 0), (0, -1), (-1, -2), (14, 13), (41, 40)]:
        r = _run("decrement", v).to_int()
        print(f"    {'✓' if r == e else '✗'}  {v:>4d} ({_bt(v):>6s})  →  {r:>4d} ({_bt(r):>6s})")

    print("\n  ── NEGATE ──")
    for v, e in [(1, -1), (-1, 1), (5, -5), (-13, 13), (0, 0), (40, -40)]:
        r = _run("negate", v).to_int()
        print(f"    {'✓' if r == e else '✗'}  {v:>4d} ({_bt(v):>6s})  →  {r:>4d} ({_bt(r):>6s})")

    print("\n  ── ADDITION ──")
    for (a, b), e in [((0, 0), 0), ((1, 1), 2), ((13, 14), 27), ((-13, 13), 0), ((40, 41), 81), ((100, 200), 300)]:
        r = _run2(a, b).to_int()
        print(f"    {'✓' if r == e else '✗'}  {a:>4d} + {b:>4d} = {r:>4d} ({_bt(r):>8s})")

    print(f"\n{SEP}")
    print("  ALGEBRAIC PROOFS")
    print(SEP)

    vals = [-40, -13, -1, 0, 1, 13, 40]

    print("\n  ▸ Symmetry: inc(dec(n)) == n == dec(inc(n))")
    ok = all(
        _run("increment", _run("decrement", n).to_int()).to_int() == n ==
        _run("decrement", _run("increment", n).to_int()).to_int()
        for n in vals
    )
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  ▸ Involution: neg(neg(n)) == n")
    ok = all(_run("negate", _run("negate", n).to_int()).to_int() == n for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  ▸ Additive inverse: n + (-n) == 0")
    ok = all(_run2(n, _run("negate", n).to_int()).to_int() == 0 for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  ▸ Commutativity: a + b == b + a")
    ok = all(_run2(a, b).to_int() == _run2(b, a).to_int() for a, b in [(1, 2), (13, -5), (-40, 27)])
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  ▸ Equivalence: inc(n) == n + 1")
    ok = all(_run("increment", n).to_int() == _run2(n, 1).to_int() for n in vals)
    print(f"    {'Passed' if ok else 'FAILED'}")

    print("\n  ▸ Distributivity: neg(a+b) == neg(a) + neg(b)")
    ok = all(
        _run("negate", _run2(a, b).to_int()).to_int() ==
        _run2(_run("negate", a).to_int(), _run("negate", b).to_int()).to_int()
        for a, b in [(1, 2), (13, -5), (-40, 27)]
    )
    print(f"    {'Passed' if ok else 'FAILED'}")

    print(f"\n{SEP}")
    print("  VM PROGRAMS")
    print(SEP)

    # Factorial(5) = 120
    print("\n  ── Factorial(5) = 120 ──")
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
        print(f"    → {line}")
    print(f"  vm_steps={vm.step_count}  alu_ticks={vm.alu_ticks}")

    # Fibonacci
    print("\n  ── Fibonacci: first 8 terms ──")
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
        print(f"    → {line}")
    actual = [int(o.split()[0]) for o in vm_fib.output]
    print(f"  {'✓' if actual == [0, 1, 1, 2, 3, 5, 8, 13] else '✗'} sequence correct")

    # Powers of 2
    print("\n  ── Powers of 2: 2^0..2^10 ──")
    prog_pow = [
        Instruction(Op.PUSH, 10), Instruction(Op.PUSH, 1),
        Instruction(Op.DUP), Instruction(Op.PRINT),
        Instruction(Op.DUP), Instruction(Op.ADD),
        Instruction(Op.SWAP), Instruction(Op.DEC),
        Instruction(Op.DUP), Instruction(Op.JN, 11),
        Instruction(Op.SWAP), Instruction(Op.JMP, 2),
        Instruction(Op.HALT),
    ]
    vm_pow = TernaryVM(prog_pow).run()
    for line in vm_pow.output:
        print(f"    → {line}")
    actual = [int(o.split()[0]) for o in vm_pow.output]
    print(f"  {'✓' if actual == [2**i for i in range(11)] else '✗'} sequence correct")


def main() -> int:
    print("\n  Trine — constraint-native balanced ternary computer\n")
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
