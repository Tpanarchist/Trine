"""Operation descriptors — injectable classification rules.

An operation is a callable that reads the current trit(s) and returns
what to write, where to move, and whether to halt. The FSM and tick
cycle are invariant. Only this changes.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Literal, NamedTuple, Optional, Tuple, TYPE_CHECKING

from .trit import Trit

if TYPE_CHECKING:
    from .model import TernaryMachineModel

MoveDirection = Literal["L", "R", "N"]
OpRule = Callable  # varies by arity
HaltCheck = Optional[Callable[["TernaryMachineModel"], bool]]


class OpDescriptor(NamedTuple):
    """Complete operation specification."""
    name: str
    rule: OpRule
    halt_check: HaltCheck = None
    uses_carry: bool = False
    binary: bool = False


# ── Halt checks ──

def halt_past_msb(model: TernaryMachineModel) -> bool:
    """Halt when head has moved left past all nonzero tape cells."""
    nz = model.tape.nonzero_indexes()
    if not nz:
        return True
    return model.head < min(nz)


def halt_addition(model: TernaryMachineModel) -> bool:
    """Halt when past both operands' MSB and carry is zero."""
    nz = list(model.tape.nonzero_indexes())
    if model.second_tape:
        nz.extend(model.second_tape.nonzero_indexes())
    if not nz:
        return model.carry is Trit.ZERO
    return model.head < min(nz) and model.carry is Trit.ZERO


# ── Unary operation rules ──

def rule_increment(symbol: Trit) -> Tuple[Trit, MoveDirection, bool]:
    """NEG→0 stay halt | ZERO→+ stay halt | POS→- left continue"""
    if symbol is Trit.NEG:
        return (Trit.ZERO, "N", True)
    if symbol is Trit.ZERO:
        return (Trit.POS, "N", True)
    if symbol is Trit.POS:
        return (Trit.NEG, "L", False)
    raise ValueError(f"invalid trit: {symbol}")


def rule_decrement(symbol: Trit) -> Tuple[Trit, MoveDirection, bool]:
    """POS→0 stay halt | ZERO→- stay halt | NEG→+ left continue"""
    if symbol is Trit.POS:
        return (Trit.ZERO, "N", True)
    if symbol is Trit.ZERO:
        return (Trit.NEG, "N", True)
    if symbol is Trit.NEG:
        return (Trit.POS, "L", False)
    raise ValueError(f"invalid trit: {symbol}")


def rule_negate(symbol: Trit) -> Tuple[Trit, MoveDirection, bool]:
    """Flip every trit, scan left. External halt at MSB."""
    return (symbol.flip(), "L", False)


# ── Binary operation rules ──

def rule_addition(a: Trit, b: Trit, carry: Trit) -> Tuple[Trit, Trit, MoveDirection, bool]:
    """Full balanced ternary adder: a + b + carry → (write, carry_out, move, halt).

    Sum range: -3 to +3. Decompose into write_trit + carry_out * 3.
    """
    s = int(a) + int(b) + int(carry)
    if s <= -2:
        return (Trit.coerce(s + 3), Trit.NEG, "L", False)
    elif s >= 2:
        return (Trit.coerce(s - 3), Trit.POS, "L", False)
    else:
        return (Trit.coerce(s), Trit.ZERO, "L", False)


# ── Operation registry ──

OP_INCREMENT = OpDescriptor("increment", rule_increment)
OP_DECREMENT = OpDescriptor("decrement", rule_decrement)
OP_NEGATE = OpDescriptor("negate", rule_negate, halt_check=halt_past_msb)
OP_ADDITION = OpDescriptor("add", rule_addition, halt_check=halt_addition, uses_carry=True, binary=True)

OPERATIONS: Dict[str, OpDescriptor] = {
    "increment": OP_INCREMENT,
    "decrement": OP_DECREMENT,
    "negate": OP_NEGATE,
    "add": OP_ADDITION,
}


# ── Composite / tape-manipulation operations ──

def shift_left(value: int) -> int:
    """Multiply by 3."""
    return value * 3


def shift_right(value: int) -> int:
    """Divide by 3, truncating toward zero."""
    if value == 0:
        return 0
    return int(value / 3) if value > 0 else -int(-value / 3)


def sign(value: int) -> int:
    """Return -1, 0, or +1."""
    return (value > 0) - (value < 0)
