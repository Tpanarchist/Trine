"""TernaryMachine — public facade for the balanced ternary ALU.

Assembles FSM + Model + Operation into a runnable machine.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from .trit import Trit
from .tape import Tape
from .formatting import int_to_trits, trits_to_int, format_trits
from .model import TernaryMachineModel
from .fsm import MiniFSM, MachineError
from .operations import (
    OpDescriptor, OPERATIONS, MoveDirection,
    shift_left, shift_right, sign,
)

# ── Reference FSM states and transitions ──

STATES: List[str] = [
    "idle", "read", "classify",
    "write_neg", "write_zero", "write_pos",
    "move_left", "move_right", "stay",
    "accept", "reject",
]

TRANSITIONS: List[Dict[str, Any]] = [
    {"trigger": "load_input", "source": "*", "dest": "idle", "before": "prepare_input"},
    {"trigger": "begin", "source": "idle", "dest": "read", "after": "read_symbol"},
    {"trigger": "advance", "source": "read", "dest": "classify", "after": "select_transition"},
    {"trigger": "advance", "source": ["move_left", "move_right", "stay"], "dest": "read", "after": "read_symbol"},
    {"trigger": "route_neg", "source": "classify", "dest": "write_neg", "after": "write_symbol"},
    {"trigger": "route_zero", "source": "classify", "dest": "write_zero", "after": "write_symbol"},
    {"trigger": "route_pos", "source": "classify", "dest": "write_pos", "after": "write_symbol"},
    {"trigger": "go_left", "source": ["write_neg", "write_zero", "write_pos"], "dest": "move_left", "after": "complete_move_phase"},
    {"trigger": "go_right", "source": ["write_neg", "write_zero", "write_pos"], "dest": "move_right", "after": "complete_move_phase"},
    {"trigger": "go_stay", "source": ["write_neg", "write_zero", "write_pos"], "dest": "stay", "after": "complete_move_phase"},
    {"trigger": "finish_accept", "source": ["move_left", "move_right", "stay"], "dest": "accept"},
    {"trigger": "finish_reject", "source": "*", "dest": "reject"},
    {"trigger": "halt", "source": "*", "dest": "reject", "before": "set_manual_halt_reason"},
]


class TernaryMachine:
    """Balanced ternary machine with injectable operations.

    Usage:
        m = TernaryMachine("increment").load_int(4).run()
        m = TernaryMachine("add").load_two(13, 27).run()
    """

    def __init__(self, operation: Union[str, OpDescriptor] = "increment") -> None:
        desc = self._resolve(operation)
        self.model = TernaryMachineModel(op=desc)
        self.control = MiniFSM(
            model=self.model, states=STATES,
            transitions=TRANSITIONS, initial="idle",
        )

    @staticmethod
    def _resolve(operation: Union[str, OpDescriptor]) -> OpDescriptor:
        if isinstance(operation, OpDescriptor):
            return operation
        name = operation.lower()
        desc = OPERATIONS.get(name)
        if desc is None:
            raise ValueError(f"unknown operation '{operation}', available: {', '.join(OPERATIONS)}")
        return desc

    @classmethod
    def _bare(cls, operation: Union[str, OpDescriptor] = "increment") -> TernaryMachine:
        obj = object.__new__(cls)
        obj.model = TernaryMachineModel(op=cls._resolve(operation))
        return obj

    # ── Properties ──

    @property
    def state(self) -> str:
        return self.model.state

    @property
    def leaf_state(self) -> str:
        return self.model.leaf_state

    @property
    def tape(self) -> Tape:
        return self.model.tape

    @property
    def head(self) -> int:
        return self.model.head

    @property
    def trace(self) -> List[str]:
        return list(self.model.trace)

    @property
    def halt_reason(self) -> Optional[str]:
        return self.model.halt_reason

    # ── Loading ──

    def load_int(self, value: int, head: int = 0) -> TernaryMachine:
        try:
            self.model.load_input(value=value, head=head)
        except Exception as exc:
            self.model.reject_with_reason(str(exc))
        return self

    def load_trits(self, trits: Iterable[int], head: int = 0) -> TernaryMachine:
        try:
            self.model.load_input(trits=list(trits), head=head)
        except Exception as exc:
            self.model.reject_with_reason(str(exc))
        return self

    def load_two(self, a: int, b: int, head: int = 0) -> TernaryMachine:
        """Load two operands for binary operations."""
        try:
            self.model.load_input(value=a, head=head)
            digits_b = int_to_trits(b)
            t2 = Tape()
            offset = len(digits_b) - 1
            for pos, digit in enumerate(digits_b):
                idx = head - (offset - pos)
                t2.write(idx, digit)
            self.model.second_tape = t2
            self.model.carry = Trit.ZERO
        except Exception as exc:
            self.model.reject_with_reason(str(exc))
        return self

    # ── Execution ──

    def step(self) -> TernaryMachine:
        leaf = self.leaf_state
        if leaf in ("accept", "reject"):
            return self
        try:
            if leaf == "idle":
                self.model.begin()
            elif leaf == "read":
                self.model.advance()
            elif leaf in ("classify", "carry_check", "overflow"):
                self._route_classification()
            elif leaf in ("write_neg", "write_zero", "write_pos"):
                self._route_move()
            elif leaf in ("move_left", "move_right", "stay"):
                if self.model.should_halt():
                    self.model.finish_accept()
                else:
                    self.model.advance()
            else:
                raise RuntimeError(f"unexpected state: {self.state}")
        except Exception as exc:
            self.model.reject_with_reason(str(exc))
        return self

    def run(self, max_steps: Optional[int] = None) -> TernaryMachine:
        while self.leaf_state not in ("accept", "reject"):
            self.step()
            if (
                max_steps is not None
                and self.model.step_count >= max_steps
                and self.leaf_state not in ("accept", "reject")
            ):
                self.model.reject_with_reason("max_steps exceeded")
        return self

    def to_int(self) -> int:
        return trits_to_int(self.model.visible_trits())

    def balanced(self) -> str:
        return self.model.balanced()

    # ── Internal routing ──

    def _route_classification(self) -> None:
        ns = self.model.next_symbol
        if ns is Trit.NEG:
            self.model.route_neg()
        elif ns is Trit.ZERO:
            self.model.route_zero()
        elif ns is Trit.POS:
            self.model.route_pos()
        else:
            raise ValueError("no valid write target after classification")

    def _route_move(self) -> None:
        d = self.model.move_direction
        if d == "L":
            self.model.go_left()
        elif d == "R":
            self.model.go_right()
        elif d == "N":
            self.model.go_stay()
        else:
            raise ValueError("invalid move direction")


# ── Composite operations ──

TickSink = Optional[Callable[[int], None]]


def _emit_ticks(tick_sink: TickSink, ticks: int) -> None:
    if tick_sink is not None and ticks:
        tick_sink(ticks)


def _run_unary_machine(operation: str, value: int) -> Tuple[int, int]:
    machine = TernaryMachine(operation).load_int(value).run()
    return machine.to_int(), machine.model.step_count


def _run_binary_machine(operation: str, a: int, b: int) -> Tuple[int, int]:
    machine = TernaryMachine(operation).load_two(a, b).run()
    return machine.to_int(), machine.model.step_count


def ternary_abs(value: int, *, tick_sink: TickSink = None) -> int:
    """Absolute value: negate if negative, identity otherwise."""
    if value < 0:
        result, ticks = _run_unary_machine("negate", value)
        _emit_ticks(tick_sink, ticks)
        return result
    return value


def ternary_sub(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Subtraction: a - b = a + negate(b)."""
    neg_b, neg_ticks = _run_unary_machine("negate", b)
    _emit_ticks(tick_sink, neg_ticks)
    result, add_ticks = _run_binary_machine("add", a, neg_b)
    _emit_ticks(tick_sink, add_ticks)
    return result


def ternary_cmp(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Comparison as a balanced trit: -1 if a<b, 0 if a==b, +1 if a>b."""
    return sign(ternary_sub(a, b, tick_sink=tick_sink))


def ternary_min(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Minimum under the existing integer ordering."""
    return a if ternary_cmp(a, b, tick_sink=tick_sink) <= 0 else b


def ternary_max(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Maximum under the existing integer ordering."""
    return a if ternary_cmp(a, b, tick_sink=tick_sink) >= 0 else b


def ternary_cons(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Consensus: return the shared value if equal, otherwise zero."""
    return a if ternary_cmp(a, b, tick_sink=tick_sink) == 0 else 0


def _ternary_divmod(a: int, b: int, *, tick_sink: TickSink = None) -> Tuple[int, int]:
    """Division with truncation toward zero and remainder matching the dividend sign."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    if a == 0:
        return 0, 0

    dividend = ternary_abs(a, tick_sink=tick_sink)
    divisor = ternary_abs(b, tick_sink=tick_sink)
    quotient = 0
    remainder = dividend

    while ternary_cmp(remainder, divisor, tick_sink=tick_sink) >= 0:
        remainder = ternary_sub(remainder, divisor, tick_sink=tick_sink)
        quotient, ticks = _run_unary_machine("increment", quotient)
        _emit_ticks(tick_sink, ticks)

    if (a < 0) != (b < 0) and quotient != 0:
        quotient, ticks = _run_unary_machine("negate", quotient)
        _emit_ticks(tick_sink, ticks)

    if a < 0 and remainder != 0:
        remainder, ticks = _run_unary_machine("negate", remainder)
        _emit_ticks(tick_sink, ticks)

    return quotient, remainder


def ternary_div(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Integer division with truncation toward zero."""
    quotient, _ = _ternary_divmod(a, b, tick_sink=tick_sink)
    return quotient


def ternary_mod(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Remainder paired with truncation-toward-zero division."""
    _, remainder = _ternary_divmod(a, b, tick_sink=tick_sink)
    return remainder


def ternary_mul(a: int, b: int, *, tick_sink: TickSink = None) -> int:
    """Multiplication via shift-and-add with trit dispatch."""
    if b == 0:
        return 0
    result = 0
    multiplicand = a
    b_trits = list(reversed(int_to_trits(b)))
    for trit in b_trits:
        if trit is Trit.POS:
            result, ticks = _run_binary_machine("add", result, multiplicand)
            _emit_ticks(tick_sink, ticks)
        elif trit is Trit.NEG:
            neg_m, neg_ticks = _run_unary_machine("negate", multiplicand)
            _emit_ticks(tick_sink, neg_ticks)
            result, add_ticks = _run_binary_machine("add", result, neg_m)
            _emit_ticks(tick_sink, add_ticks)
        multiplicand = shift_left(multiplicand)
    return result
