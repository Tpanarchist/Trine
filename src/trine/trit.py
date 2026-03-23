"""Ternary symbol primitives — the irreducible foundation of Trine."""

from __future__ import annotations

from enum import IntEnum
from typing import Iterable, List, Union

TritLike = Union["Trit", int]


class Trit(IntEnum):
    """Balanced ternary symbol: {-1, 0, +1}.

    Symmetric around zero. No sign bit. No unsigned type.
    Integer-compatible via IntEnum. Identity: -Trit == flip.
    """

    NEG = -1
    ZERO = 0
    POS = 1

    @classmethod
    def coerce(cls, value: TritLike) -> Trit:
        """Convert int or Trit to canonical Trit. Raises on invalid input."""
        if isinstance(value, cls):
            return value
        try:
            return cls(int(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("trit values must be -1, 0, or +1") from exc

    @property
    def label(self) -> str:
        return _LABELS[self]

    @property
    def symbol(self) -> str:
        return _SYMBOLS[self]

    def flip(self) -> Trit:
        """Negate: NEG↔POS, ZERO→ZERO."""
        return Trit.coerce(-int(self))

    def __str__(self) -> str:
        return self.label

    def __repr__(self) -> str:
        return f"Trit.{self.label}"


# Pre-built lookup tables (avoid dict creation per call)
_LABELS = {Trit.NEG: "NEG", Trit.ZERO: "ZERO", Trit.POS: "POS"}
_SYMBOLS = {Trit.NEG: "-", Trit.ZERO: "0", Trit.POS: "+"}


def coerce_trits(values: Iterable[TritLike]) -> List[Trit]:
    """Coerce an iterable of int-like values to a list of Trits."""
    return [Trit.coerce(v) for v in values]
