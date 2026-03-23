"""TernaryMachineModel — computational callbacks for the FSM tick cycle.

The FSM controls what transitions are permitted.
The model controls what happens when they fire.
These never leak into each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from .trit import Trit, coerce_trits
from .tape import Tape
from .formatting import format_trits, int_to_trits, tape_to_trits
from .operations import MoveDirection, OpDescriptor


@dataclass
class TernaryMachineModel:
    tape: Tape = field(default_factory=Tape)
    head: int = 0
    least_significant_index: int = 0
    current_symbol: Optional[Trit] = None
    next_symbol: Optional[Trit] = None
    move_direction: Optional[MoveDirection] = None
    step_count: int = 0
    halt_reason: Optional[str] = None
    trace: List[str] = field(default_factory=list)
    pending_accept: bool = False
    state: str = "idle"
    # Operation descriptor
    op: Optional[OpDescriptor] = None
    # Carry register for binary operations
    carry: Trit = field(default=Trit.ZERO)
    # Second tape for binary operations (operand B, read-only)
    second_tape: Optional[Tape] = None

    @property
    def leaf_state(self) -> str:
        """Rightmost component of a dot-separated hierarchical state."""
        s = self.state
        return s.rsplit(".", 1)[-1] if "." in s else s

    # ── Input loading ──

    def prepare_input(self, event: Any = None) -> None:
        kwargs = event.kwargs if event else {}
        lsd_index = int(kwargs.get("head", 0))
        if "trits" in kwargs and "value" in kwargs:
            raise ValueError("provide either trits or value, not both")
        if "trits" in kwargs:
            digits = coerce_trits(kwargs["trits"])
        elif "value" in kwargs:
            digits = int_to_trits(kwargs["value"])
        else:
            raise ValueError("load_input requires either trits or value")
        if not digits:
            raise ValueError("trit sequence must not be empty")

        new_tape = Tape()
        offset = len(digits) - 1
        for position, digit in enumerate(digits):
            index = lsd_index - (offset - position)
            new_tape.write(index, digit)

        self.tape = new_tape
        self.head = lsd_index
        self.least_significant_index = lsd_index
        self.current_symbol = None
        self.next_symbol = None
        self.move_direction = None
        self.step_count = 0
        self.halt_reason = None
        self.trace = []
        self.pending_accept = False
        self.carry = Trit.ZERO

    # ── Tick cycle callbacks ──

    def read_symbol(self, event: Any = None) -> None:
        self.current_symbol = self.tape.read(self.head)
        self.next_symbol = None
        self.move_direction = None
        self.pending_accept = False

    def select_transition(self, event: Any = None) -> None:
        """Delegate classification to the injected operation."""
        if self.op is None:
            raise ValueError("no operation set on model")
        if self.op.uses_carry:
            b = self.second_tape.read(self.head) if self.second_tape else Trit.ZERO
            write_trit, carry_out, move_dir, should_accept = self.op.rule(
                self.current_symbol, b, self.carry
            )
            self.carry = carry_out
        else:
            write_trit, move_dir, should_accept = self.op.rule(self.current_symbol)
        self.next_symbol = write_trit
        self.move_direction = move_dir
        self.pending_accept = should_accept

    def write_symbol(self, event: Any = None) -> None:
        if self.next_symbol is None:
            raise ValueError("next_symbol must be selected before writing")
        expected_leaf = {
            Trit.NEG: "write_neg",
            Trit.ZERO: "write_zero",
            Trit.POS: "write_pos",
        }[self.next_symbol]
        if self.leaf_state != expected_leaf:
            raise ValueError(
                f"write state mismatch: leaf='{self.leaf_state}' expected='{expected_leaf}'"
            )
        self.tape.write(self.head, self.next_symbol)

    def move_head(self, event: Any = None) -> None:
        leaf = self.leaf_state
        if leaf == "move_left" and self.move_direction != "L":
            raise ValueError("move_left requires L")
        if leaf == "move_right" and self.move_direction != "R":
            raise ValueError("move_right requires R")
        if leaf == "stay" and self.move_direction != "N":
            raise ValueError("stay requires N")
        if self.move_direction == "L":
            self.head -= 1
        elif self.move_direction == "R":
            self.head += 1
        elif self.move_direction == "N":
            pass
        else:
            raise ValueError("invalid move direction")

    def complete_move_phase(self, event: Any = None) -> None:
        self.move_head()
        self.step_count += 1
        self.record_trace()

    def record_trace(self, event: Any = None) -> None:
        tape_view = self.tape.snapshot(self.head, radius=4)
        outcome = "accept" if self.should_halt() else "continue"
        extra = f" carry={self.carry.symbol}" if self.op and self.op.uses_carry else ""
        line = (
            f"step={self.step_count:02d} state={self.state} head={self.head} "
            f"read={self._fmt(self.current_symbol)} "
            f"write={self._fmt(self.next_symbol)} "
            f"move={self.move_direction or '?'} outcome={outcome}{extra} "
            f"tape={tape_view}"
        )
        self.trace.append(line)

    # ── Guards ──

    def is_neg(self, event: Any = None) -> bool:
        return self.current_symbol is Trit.NEG

    def is_zero(self, event: Any = None) -> bool:
        return self.current_symbol is Trit.ZERO

    def is_pos(self, event: Any = None) -> bool:
        return self.current_symbol is Trit.POS

    def should_halt(self, event: Any = None) -> bool:
        if self.op and self.op.halt_check is not None:
            return self.op.halt_check(self)
        return self.pending_accept

    # ── Error handling ──

    def reject_with_reason(self, reason: str) -> None:
        self.halt_reason = reason
        self.pending_accept = False
        try:
            if self.leaf_state != "reject":
                self.finish_reject()
        except (Exception,):
            self.state = "reject"

    def set_manual_halt_reason(self, event: Any = None) -> None:
        kwargs = event.kwargs if event else {}
        self.halt_reason = kwargs.get("reason", "halt requested")
        self.pending_accept = False

    # ── Output ──

    def visible_trits(self) -> list:
        return tape_to_trits(self.tape, self.least_significant_index)

    def balanced(self) -> str:
        return format_trits(self.visible_trits())

    def active_path(self) -> list:
        s = self.state
        return s.split(".") if "." in s else [s]

    @staticmethod
    def _fmt(symbol) -> str:
        return "None" if symbol is None else symbol.label
