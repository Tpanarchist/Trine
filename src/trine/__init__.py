"""Trine — a constraint-native balanced ternary computer."""

from .trit import Trit, TritLike, coerce_trits
from .tape import Tape
from .formatting import int_to_trits, trits_to_int, format_trits, tape_to_trits
from .operations import (
    OpDescriptor, OPERATIONS,
    rule_increment, rule_decrement, rule_negate, rule_addition,
    shift_left, shift_right, sign,
)
from .assembler import (
    AssemblerError,
    assemble,
    assemble_image,
    assemble_file,
    assemble_file_image,
    assemble_lines,
    assemble_lines_image,
)
from .fsm import MiniFSM, MachineError
from .model import TernaryMachineModel
from .machine import (
    TernaryMachine,
    ternary_abs,
    ternary_sub,
    ternary_cmp,
    ternary_min,
    ternary_max,
    ternary_cons,
    ternary_div,
    ternary_mod,
    ternary_mul,
)
from .vm import TernaryVM, Instruction, Op, ProgramImage, VMError

__all__ = [
    "Trit", "TritLike", "coerce_trits",
    "Tape",
    "int_to_trits", "trits_to_int", "format_trits", "tape_to_trits",
    "OpDescriptor", "OPERATIONS",
    "rule_increment", "rule_decrement", "rule_negate", "rule_addition",
    "shift_left", "shift_right", "sign",
    "AssemblerError",
    "assemble",
    "assemble_image",
    "assemble_file",
    "assemble_file_image",
    "assemble_lines",
    "assemble_lines_image",
    "CompileError",
    "compile_source",
    "compile_file",
    "compile_program",
    "compile_image",
    "compile_file_program",
    "compile_file_image",
    "MiniFSM", "MachineError",
    "TernaryMachineModel",
    "TernaryMachine",
    "ternary_abs",
    "ternary_sub",
    "ternary_cmp",
    "ternary_min",
    "ternary_max",
    "ternary_cons",
    "ternary_div",
    "ternary_mod",
    "ternary_mul",
    "TernaryVM", "Instruction", "Op", "ProgramImage", "VMError",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    if name in {
        "CompileError",
        "compile_source",
        "compile_file",
        "compile_program",
        "compile_image",
        "compile_file_program",
        "compile_file_image",
    }:
        from . import compiler as _compiler

        return getattr(_compiler, name)
    raise AttributeError(f"module 'trine' has no attribute '{name}'")
