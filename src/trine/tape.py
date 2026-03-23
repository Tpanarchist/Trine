"""Sparse ternary tape — unbounded, default-zero, write-zero-deletes."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional

from .trit import Trit, TritLike


class Tape:
    """Sparse balanced ternary memory.

    Conceptually infinite in both directions. Unwritten cells read as ZERO.
    Writing ZERO to a cell deletes it from storage (sparsity invariant).
    """

    __slots__ = ("_cells",)

    def __init__(self, initial: Optional[Mapping[int, TritLike]] = None) -> None:
        self._cells: Dict[int, Trit] = {}
        if initial:
            for index, value in initial.items():
                self.write(index, value)

    def read(self, index: int) -> Trit:
        return self._cells.get(index, Trit.ZERO)

    def write(self, index: int, value: TritLike) -> None:
        trit = Trit.coerce(value)
        if trit is Trit.ZERO:
            self._cells.pop(index, None)
        else:
            self._cells[index] = trit

    def snapshot(self, center: int, radius: int = 8) -> str:
        """Human-readable window around `center`. Head position bracketed."""
        parts: List[str] = []
        for i in range(center - radius, center + radius + 1):
            token = f"{i}:{self.read(i).symbol}"
            if i == center:
                token = f"[{token}]"
            parts.append(token)
        return " ".join(parts)

    def nonzero_indexes(self) -> List[int]:
        return sorted(self._cells.keys())

    def as_dict(self) -> Dict[int, Trit]:
        return dict(self._cells)

    def clear(self) -> None:
        self._cells.clear()

    def __len__(self) -> int:
        return len(self._cells)
