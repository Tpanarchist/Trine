"""Balanced ternary formatting and conversion."""

from __future__ import annotations

from typing import Iterable, List

from .tape import Tape
from .trit import Trit, TritLike, coerce_trits


def int_to_trits(value: int) -> List[Trit]:
    """Convert integer to balanced ternary digits, most-significant first."""
    if not isinstance(value, int):
        raise ValueError("value must be an integer")
    if value == 0:
        return [Trit.ZERO]
    digits: List[Trit] = []
    remaining = value
    while remaining != 0:
        remaining, r = divmod(remaining, 3)
        if r == 2:
            r = -1
            remaining += 1
        digits.append(Trit.coerce(r))
    digits.reverse()
    return digits


def trits_to_int(values: Iterable[TritLike]) -> int:
    """Convert balanced ternary digits (MSB first) to integer."""
    digits = coerce_trits(values)
    if not digits:
        raise ValueError("trit sequence must not be empty")
    total = 0
    for trit in digits:
        total = (total * 3) + int(trit)
    return total


def format_trits(values: Iterable[TritLike], separator: str = "") -> str:
    """Format trits as a symbol string: + 0 -"""
    return separator.join(t.symbol for t in coerce_trits(values))


def tape_to_trits(tape: Tape, least_significant_index: int = 0) -> List[Trit]:
    """Read canonical digit sequence from tape."""
    nz = tape.nonzero_indexes()
    if not nz:
        return [Trit.ZERO]
    start = min(nz)
    stop = least_significant_index
    if start > stop:
        raise ValueError("least_significant_index must be at or right of digits")
    return [tape.read(i) for i in range(start, stop + 1)]
