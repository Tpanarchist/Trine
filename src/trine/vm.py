"""TernaryVM — stored-program stack machine on the ALU substrate.

Harvard architecture: separate program (instruction list) and data (stack).
All arithmetic dispatches to TernaryMachine. The VM never does math directly.
Three-way branching (BR3) is a primitive instruction.
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from .trit import Trit
from .formatting import format_trits, int_to_trits
from .machine import TernaryMachine, ternary_abs, ternary_sub, ternary_mul
from .operations import shift_left, shift_right, sign


# ── Opcodes ──

class Op:
    # Stack
    PUSH  = "PUSH"
    DUP   = "DUP"
    SWAP  = "SWAP"
    POP   = "POP"
    OVER  = "OVER"
    # Unary ALU
    INC   = "INC"
    DEC   = "DEC"
    NEG   = "NEG"
    ABS   = "ABS"
    SHL   = "SHL"
    SHR   = "SHR"
    SGN   = "SGN"
    # Binary ALU
    ADD   = "ADD"
    SUB   = "SUB"
    MUL   = "MUL"
    # Control flow
    JMP   = "JMP"
    JN    = "JN"
    JZ    = "JZ"
    JP    = "JP"
    BR3   = "BR3"
    # I/O
    PRINT = "PRINT"
    HALT  = "HALT"


class Instruction(NamedTuple):
    op: str
    operand: Any = None

    def __repr__(self) -> str:
        return f"{self.op} {self.operand}" if self.operand is not None else self.op


class VMError(Exception):
    pass


class TernaryVM:
    """Stack-based ternary VM. All arithmetic via ALU dispatch."""

    def __init__(self, program: List[Instruction], max_steps: int = 10000) -> None:
        self.program = program
        self.stack: List[int] = []
        self.pc: int = 0
        self.halted: bool = False
        self.trace: List[str] = []
        self.output: List[str] = []
        self.step_count: int = 0
        self.alu_ticks: int = 0
        self.max_steps = max_steps

    def reset(self) -> TernaryVM:
        self.stack = []
        self.pc = 0
        self.halted = False
        self.trace = []
        self.output = []
        self.step_count = 0
        self.alu_ticks = 0
        return self

    def _push(self, value: int) -> None:
        self.stack.append(value)

    def _pop(self) -> int:
        if not self.stack:
            raise VMError(f"stack underflow at pc={self.pc}")
        return self.stack.pop()

    def _peek(self) -> int:
        if not self.stack:
            raise VMError(f"stack underflow (peek) at pc={self.pc}")
        return self.stack[-1]

    def _alu_unary(self, op_name: str, value: int) -> int:
        if op_name == "abs":
            return ternary_abs(value)
        if op_name == "sign":
            return sign(value)
        if op_name == "shift_left":
            return shift_left(value)
        if op_name == "shift_right":
            return shift_right(value)
        m = TernaryMachine(op_name).load_int(value).run(max_steps=500)
        self.alu_ticks += m.model.step_count
        if m.leaf_state == "reject":
            raise VMError(f"ALU rejected: {op_name}({value}) — {m.halt_reason}")
        return m.to_int()

    def _alu_add(self, a: int, b: int) -> int:
        # Scale max_steps to operand size (large numbers need more ticks)
        digits = max(len(str(abs(a))) if a else 1, len(str(abs(b))) if b else 1)
        limit = max(500, digits * 5)
        m = TernaryMachine("add").load_two(a, b).run(max_steps=limit)
        self.alu_ticks += m.model.step_count
        if m.leaf_state == "reject":
            raise VMError(f"ALU rejected: add({a}, {b}) — {m.halt_reason}")
        return m.to_int()

    def step(self) -> bool:
        if self.halted or self.pc >= len(self.program):
            self.halted = True
            return False

        instr = self.program[self.pc]
        self.trace.append(
            f"  [{self.step_count:04d}] pc={self.pc:03d} {str(instr):<16s} stack={list(self.stack)}"
        )
        self.step_count += 1
        if self.step_count > self.max_steps:
            raise VMError(f"exceeded max_steps ({self.max_steps})")

        op = instr.op
        next_pc = self.pc + 1

        # Stack manipulation
        if op == Op.PUSH:
            self._push(instr.operand)
        elif op == Op.DUP:
            self._push(self._peek())
        elif op == Op.SWAP:
            b, a = self._pop(), self._pop()
            self._push(b)
            self._push(a)
        elif op == Op.POP:
            self._pop()
        elif op == Op.OVER:
            b = self._pop()
            a = self._peek()
            self._push(b)
            self._push(a)

        # Unary ALU
        elif op == Op.INC:
            self._push(self._alu_unary("increment", self._pop()))
        elif op == Op.DEC:
            self._push(self._alu_unary("decrement", self._pop()))
        elif op == Op.NEG:
            self._push(self._alu_unary("negate", self._pop()))
        elif op == Op.ABS:
            self._push(self._alu_unary("abs", self._pop()))
        elif op == Op.SHL:
            self._push(self._alu_unary("shift_left", self._pop()))
        elif op == Op.SHR:
            self._push(self._alu_unary("shift_right", self._pop()))
        elif op == Op.SGN:
            self._push(self._alu_unary("sign", self._pop()))

        # Binary ALU
        elif op == Op.ADD:
            b, a = self._pop(), self._pop()
            self._push(self._alu_add(a, b))
        elif op == Op.SUB:
            b, a = self._pop(), self._pop()
            neg_b = self._alu_unary("negate", b)
            self._push(self._alu_add(a, neg_b))
        elif op == Op.MUL:
            b, a = self._pop(), self._pop()
            self._push(ternary_mul(a, b))

        # Control flow
        elif op == Op.JMP:
            next_pc = instr.operand
        elif op == Op.JN:
            if self._pop() < 0:
                next_pc = instr.operand
        elif op == Op.JZ:
            if self._pop() == 0:
                next_pc = instr.operand
        elif op == Op.JP:
            if self._pop() > 0:
                next_pc = instr.operand
        elif op == Op.BR3:
            val = self._pop()
            neg_t, zero_t, pos_t = instr.operand
            next_pc = neg_t if val < 0 else (zero_t if val == 0 else pos_t)

        # I/O
        elif op == Op.PRINT:
            val = self._pop()
            self.output.append(f"{val} ({format_trits(int_to_trits(val))})")
        elif op == Op.HALT:
            self.halted = True
            return False
        else:
            raise VMError(f"unknown opcode: {op}")

        self.pc = next_pc
        return True

    def run(self) -> TernaryVM:
        while self.step():
            pass
        return self
