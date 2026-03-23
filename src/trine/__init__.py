"""Trine — a constraint-native balanced ternary computer."""

from .trit import Trit, TritLike, coerce_trits
from .tape import Tape
from .formatting import int_to_trits, trits_to_int, format_trits, tape_to_trits
from .operations import (
    OpDescriptor, OPERATIONS,
    rule_increment, rule_decrement, rule_negate, rule_addition,
    shift_left, shift_right, sign,
)
from .fsm import MiniFSM, MachineError
from .model import TernaryMachineModel
from .machine import TernaryMachine, ternary_abs, ternary_sub, ternary_mul
from .vm import TernaryVM, Instruction, Op, VMError

__all__ = [
    "Trit", "TritLike", "coerce_trits",
    "Tape",
    "int_to_trits", "trits_to_int", "format_trits", "tape_to_trits",
    "OpDescriptor", "OPERATIONS",
    "rule_increment", "rule_decrement", "rule_negate", "rule_addition",
    "shift_left", "shift_right", "sign",
    "MiniFSM", "MachineError",
    "TernaryMachineModel",
    "TernaryMachine", "ternary_abs", "ternary_sub", "ternary_mul",
    "TernaryVM", "Instruction", "Op", "VMError",
]

__version__ = "0.1.0"
