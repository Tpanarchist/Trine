"""Minimal assembler for line-oriented Trine assembly text."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .vm import Instruction, Op


class AssemblerError(ValueError):
    """Raised when assembly text cannot be parsed."""


_NO_OPERAND_OPS = {
    Op.DUP, Op.SWAP, Op.POP, Op.OVER,
    Op.INC, Op.DEC, Op.NEG, Op.ABS, Op.SHL, Op.SHR, Op.SGN,
    Op.ADD, Op.SUB, Op.CMP, Op.MUL,
    Op.LOAD, Op.STORE,
    Op.PRINT, Op.HALT,
}

_VALUE_OPERAND_OPS = {Op.PUSH}
_TARGET_OPERAND_OPS = {Op.JMP, Op.JN, Op.JZ, Op.JP}

_ALL_OPS = _NO_OPERAND_OPS | _VALUE_OPERAND_OPS | _TARGET_OPERAND_OPS | {Op.BR3}
_LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*)\s*:(?P<rest>.*)$")


def assemble(source: str) -> List[Instruction]:
    """Parse line-oriented assembly text into VM instructions."""
    labels: Dict[str, int] = {}
    pending: List[Tuple[int, str]] = []
    for lineno, raw_line in enumerate(source.splitlines(), start=1):
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        label, remainder = _split_label(line)
        if label is not None:
            if label in labels:
                raise AssemblerError(f"line {lineno}: duplicate label '{label}'")
            labels[label] = len(pending)
            line = remainder.strip()
            if not line:
                continue
        pending.append((lineno, line))
    return [_parse_line(line, lineno, labels) for lineno, line in pending]


def assemble_lines(lines: Iterable[str]) -> List[Instruction]:
    return assemble("\n".join(lines))


def assemble_file(path: str | Path) -> List[Instruction]:
    return assemble(Path(path).read_text(encoding="utf-8"))


def _strip_comment(line: str) -> str:
    comment_start = line.find(";")
    if comment_start == -1:
        return line
    return line[:comment_start]


def _split_label(line: str) -> Tuple[str | None, str]:
    match = _LABEL_RE.match(line)
    if match is None:
        return None, line
    return match.group("label"), match.group("rest")


def _parse_line(line: str, lineno: int, labels: Dict[str, int]) -> Instruction:
    parts = line.split(None, 1)
    opcode = parts[0].upper()
    operand_text = parts[1].strip() if len(parts) > 1 else None

    if opcode not in _ALL_OPS:
        raise AssemblerError(f"line {lineno}: unknown opcode '{opcode}'")

    if opcode in _NO_OPERAND_OPS:
        if operand_text is not None:
            raise AssemblerError(f"line {lineno}: opcode '{opcode}' takes no operand")
        return Instruction(opcode)

    if opcode in _VALUE_OPERAND_OPS:
        if operand_text is None:
            raise AssemblerError(f"line {lineno}: opcode '{opcode}' requires an integer operand")
        return Instruction(opcode, _parse_int(operand_text, lineno, opcode))

    if opcode in _TARGET_OPERAND_OPS:
        if operand_text is None:
            raise AssemblerError(f"line {lineno}: opcode '{opcode}' requires a target operand")
        return Instruction(opcode, _parse_target(operand_text, lineno, opcode, labels))

    if operand_text is None:
        raise AssemblerError(f"line {lineno}: opcode '{opcode}' requires three targets")
    return Instruction(opcode, _parse_br3(operand_text, lineno, labels))


def _parse_int(text: str, lineno: int, opcode: str) -> int:
    try:
        return int(text)
    except ValueError as exc:
        raise AssemblerError(
            f"line {lineno}: opcode '{opcode}' requires an integer operand"
        ) from exc


def _parse_target(text: str, lineno: int, opcode: str, labels: Dict[str, int]) -> int:
    try:
        return int(text)
    except ValueError:
        if text in labels:
            return labels[text]
    raise AssemblerError(f"line {lineno}: opcode '{opcode}' requires a valid target")


def _parse_br3(text: str, lineno: int, labels: Dict[str, int]) -> Tuple[int, int, int]:
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3 or any(not part for part in parts):
        raise AssemblerError(
            f"line {lineno}: opcode 'BR3' requires three comma-separated targets"
        )
    try:
        return tuple(_parse_target(part, lineno, "BR3", labels) for part in parts)  # type: ignore[return-value]
    except AssemblerError as exc:
        raise AssemblerError(
            f"line {lineno}: opcode 'BR3' requires three comma-separated targets"
        ) from exc
