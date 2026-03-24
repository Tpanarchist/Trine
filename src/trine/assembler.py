"""Assembler for Trine assembly text with directives, includes, and macros."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from .vm import Instruction, Op, ProgramImage


class AssemblerError(ValueError):
    """Raised when assembly text cannot be parsed."""


_NO_OPERAND_OPS = {
    Op.DUP, Op.SWAP, Op.POP, Op.OVER, Op.ROT,
    Op.INC, Op.DEC, Op.NEG, Op.ABS, Op.SHL, Op.SHR, Op.SGN,
    Op.ADD, Op.SUB, Op.CMP, Op.MIN, Op.MAX, Op.CONS, Op.DIV, Op.MOD, Op.MUL,
    Op.LOAD, Op.STORE,
    Op.PRINT, Op.HALT,
}

_VALUE_OPERAND_OPS = {Op.PUSH}
_TARGET_OPERAND_OPS = {Op.JMP, Op.JN, Op.JZ, Op.JP}
_DIRECTIVES = {"DEF", "INCLUDE", "ORG", "DATA", "MACRO", "ENDMACRO"}
_ALL_OPS = _NO_OPERAND_OPS | _VALUE_OPERAND_OPS | _TARGET_OPERAND_OPS | {Op.BR3}
_LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*)\s*:(?P<rest>.*)$")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INCLUDE_RE = re.compile(r'^INCLUDE\s+"(?P<path>[^"]+)"\s*$')
_LOCAL_LABEL_RE = re.compile(r"(?<![A-Za-z0-9_])@([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True)
class _SourceLine:
    text: str
    lineno: int
    source: str
    base_dir: Optional[Path]

    @property
    def location(self) -> str:
        return f"{self.source}:{self.lineno}"


@dataclass(frozen=True)
class _Macro:
    name: str
    params: Tuple[str, ...]
    body: Tuple[_SourceLine, ...]


@dataclass(frozen=True)
class _CodeEntry:
    text: str
    line: _SourceLine


@dataclass(frozen=True)
class _DataEntry:
    tokens: Tuple[str, ...]
    addresses: Tuple[int, ...]
    line: _SourceLine


@dataclass
class _PreprocessState:
    constants: Dict[str, int] = field(default_factory=dict)
    macros: Dict[str, _Macro] = field(default_factory=dict)
    included_paths: Set[Path] = field(default_factory=set)
    macro_expansion_count: int = 0

    def next_macro_prefix(self) -> str:
        prefix = f"__macro_{self.macro_expansion_count}_"
        self.macro_expansion_count += 1
        return prefix


def assemble(source: str, *, base_dir: str | Path | None = None) -> List[Instruction]:
    """Parse assembly text into a lowered VM program."""
    return _assemble_source(
        source=source,
        source_name="<string>",
        base_dir=Path(base_dir) if base_dir is not None else None,
        emit_prologue=True,
    )


def assemble_image(
    source: str,
    *,
    base_dir: str | Path | None = None,
) -> ProgramImage:
    """Parse assembly text into a program image with initialized memory."""
    return _assemble_source(
        source=source,
        source_name="<string>",
        base_dir=Path(base_dir) if base_dir is not None else None,
        emit_prologue=False,
    )


def assemble_lines(
    lines: Iterable[str],
    *,
    base_dir: str | Path | None = None,
) -> List[Instruction]:
    return assemble("\n".join(lines), base_dir=base_dir)


def assemble_lines_image(
    lines: Iterable[str],
    *,
    base_dir: str | Path | None = None,
) -> ProgramImage:
    return assemble_image("\n".join(lines), base_dir=base_dir)


def assemble_file(path: str | Path) -> List[Instruction]:
    file_path = Path(path)
    return _assemble_source(
        source=file_path.read_text(encoding="utf-8"),
        source_name=str(file_path),
        base_dir=file_path.parent,
        emit_prologue=True,
    )


def assemble_file_image(path: str | Path) -> ProgramImage:
    file_path = Path(path)
    return _assemble_source(
        source=file_path.read_text(encoding="utf-8"),
        source_name=str(file_path),
        base_dir=file_path.parent,
        emit_prologue=False,
    )


def _assemble_source(
    source: str,
    source_name: str,
    base_dir: Optional[Path],
    *,
    emit_prologue: bool,
) -> Union[List[Instruction], ProgramImage]:
    state = _PreprocessState()
    raw_lines = [
        _SourceLine(
            text=line,
            lineno=lineno,
            source=source_name,
            base_dir=base_dir,
        )
        for lineno, line in enumerate(source.splitlines(), start=1)
    ]
    processed = _preprocess_lines(raw_lines, state)
    if emit_prologue:
        return _build_lowered_program(processed, state.constants)
    return _build_program_image(processed, state.constants)


def _preprocess_lines(
    lines: Sequence[_SourceLine],
    state: _PreprocessState,
    *,
    include_stack: Optional[List[Path]] = None,
    macro_stack: Optional[List[str]] = None,
) -> List[_SourceLine]:
    include_stack = [] if include_stack is None else include_stack
    macro_stack = [] if macro_stack is None else macro_stack
    out: List[_SourceLine] = []
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = _strip_comment(raw_line.text).strip()
        if not stripped:
            i += 1
            continue
        label, remainder = _split_label(stripped)
        text = remainder.strip() if label is not None else stripped
        token = _first_token(text)
        upper_token = token.upper() if token is not None else None

        if upper_token == "MACRO":
            if label is not None:
                raise AssemblerError(f"{raw_line.location}: labels are not allowed on MACRO")
            macro, consumed_index = _parse_macro_definition(lines, i, state)
            macro_key = macro.name.upper()
            if macro_key in state.macros:
                raise AssemblerError(f"{raw_line.location}: duplicate MACRO '{macro.name}'")
            state.macros[macro_key] = macro
            i = consumed_index + 1
            continue

        if upper_token == "ENDMACRO":
            raise AssemblerError(f"{raw_line.location}: ENDMACRO without MACRO")

        if upper_token == "INCLUDE":
            if label is not None:
                raise AssemblerError(f"{raw_line.location}: labels are not allowed on INCLUDE")
            include_path = _resolve_include_path(text, raw_line)
            if include_path in include_stack:
                raise AssemblerError(f"{raw_line.location}: include cycle detected for '{include_path.name}'")
            if include_path in state.included_paths:
                raise AssemblerError(f"{raw_line.location}: duplicate include '{include_path.name}'")
            if not include_path.exists():
                raise AssemblerError(f"{raw_line.location}: include not found '{include_path}'")
            state.included_paths.add(include_path)
            included_lines = [
                _SourceLine(
                    text=line,
                    lineno=lineno,
                    source=str(include_path),
                    base_dir=include_path.parent,
                )
                for lineno, line in enumerate(include_path.read_text(encoding="utf-8").splitlines(), start=1)
            ]
            out.extend(
                _preprocess_lines(
                    included_lines,
                    state,
                    include_stack=include_stack + [include_path],
                    macro_stack=macro_stack,
                )
            )
            i += 1
            continue

        if upper_token == "DEF":
            if label is not None:
                raise AssemblerError(f"{raw_line.location}: labels are not allowed on DEF")
            _parse_definition(text, raw_line, state)
            i += 1
            continue

        if token is not None and token.upper() in state.macros:
            if label is not None:
                out.append(
                    _SourceLine(
                        text=f"{label}:",
                        lineno=raw_line.lineno,
                        source=raw_line.source,
                        base_dir=raw_line.base_dir,
                    )
                )
            macro = state.macros[token.upper()]
            if macro.name.upper() in macro_stack:
                raise AssemblerError(f"{raw_line.location}: macro recursion detected for '{macro.name}'")
            expanded = _expand_macro(text, raw_line, macro, state)
            out.extend(
                _preprocess_lines(
                    expanded,
                    state,
                    include_stack=include_stack,
                    macro_stack=macro_stack + [macro.name.upper()],
                )
            )
            i += 1
            continue

        out.append(
            _SourceLine(
                text=stripped,
                lineno=raw_line.lineno,
                source=raw_line.source,
                base_dir=raw_line.base_dir,
            )
        )
        i += 1
    return out


def _parse_macro_definition(
    lines: Sequence[_SourceLine],
    start_index: int,
    state: _PreprocessState,
) -> Tuple[_Macro, int]:
    header_line = lines[start_index]
    stripped = _strip_comment(header_line.text).strip()
    parts = stripped.split()
    if len(parts) < 2:
        raise AssemblerError(f"{header_line.location}: MACRO requires a name")
    name = parts[1]
    params = tuple(parts[2:])
    _require_name(name, header_line, "macro")
    for param in params:
        _require_name(param, header_line, "macro parameter")

    body: List[_SourceLine] = []
    i = start_index + 1
    while i < len(lines):
        line = lines[i]
        stripped_body = _strip_comment(line.text).strip()
        if not stripped_body:
            i += 1
            continue
        label, remainder = _split_label(stripped_body)
        text = remainder.strip() if label is not None else stripped_body
        keyword = _first_token(text)
        upper_keyword = keyword.upper() if keyword is not None else None
        if upper_keyword == "MACRO":
            raise AssemblerError(f"{line.location}: nested MACRO definitions are not allowed")
        if upper_keyword == "ENDMACRO":
            return _Macro(name=name, params=params, body=tuple(body)), i
        body.append(
            _SourceLine(
                text=stripped_body,
                lineno=line.lineno,
                source=line.source,
                base_dir=line.base_dir,
            )
        )
        i += 1
    raise AssemblerError(f"{header_line.location}: MACRO '{name}' is missing ENDMACRO")


def _parse_definition(text: str, line: _SourceLine, state: _PreprocessState) -> None:
    parts = text.split(None, 2)
    if len(parts) != 3:
        raise AssemblerError(f"{line.location}: DEF requires a name and integer value")
    _, name, value_text = parts
    _require_name(name, line, "constant")
    if name in state.constants:
        raise AssemblerError(f"{line.location}: duplicate DEF '{name}'")
    if name.upper() in state.macros:
        raise AssemblerError(f"{line.location}: constant '{name}' conflicts with existing MACRO")
    if name.upper() in _ALL_OPS or name.upper() in _DIRECTIVES:
        raise AssemblerError(f"{line.location}: constant '{name}' conflicts with assembler syntax")
    state.constants[name] = _resolve_constant_token(value_text, state.constants, line)


def _expand_macro(
    text: str,
    call_site: _SourceLine,
    macro: _Macro,
    state: _PreprocessState,
) -> List[_SourceLine]:
    parts = text.split()
    args = parts[1:]
    if len(args) != len(macro.params):
        raise AssemblerError(
            f"{call_site.location}: macro '{macro.name}' expects {len(macro.params)} args, got {len(args)}"
        )
    mapping = dict(zip(macro.params, args))
    prefix = state.next_macro_prefix()
    expanded: List[_SourceLine] = []
    for body_line in macro.body:
        rendered = body_line.text
        for name, value in mapping.items():
            rendered = rendered.replace(f"{{{name}}}", value)
        rendered = _LOCAL_LABEL_RE.sub(lambda match: f"{prefix}{match.group(1)}", rendered)
        expanded.append(
            _SourceLine(
                text=rendered,
                lineno=body_line.lineno,
                source=body_line.source,
                base_dir=body_line.base_dir,
            )
        )
    return expanded


def _build_program_image(lines: Sequence[_SourceLine], constants: Dict[str, int]) -> ProgramImage:
    code_entries, data_entries, code_labels, data_labels = _plan_layout(lines, constants)
    initial_memory = _materialize_initial_memory(
        data_entries,
        constants,
        code_labels,
        data_labels,
        code_offset=0,
    )
    instructions = [
        _parse_instruction(
            entry.text,
            entry.line,
            constants,
            code_labels,
            data_labels,
            code_offset=0,
        )
        for entry in code_entries
    ]
    return ProgramImage(instructions=instructions, initial_memory=initial_memory)


def _build_lowered_program(lines: Sequence[_SourceLine], constants: Dict[str, int]) -> List[Instruction]:
    code_entries, data_entries, code_labels, data_labels = _plan_layout(lines, constants)
    code_offset = 0
    while True:
        initial_memory = _materialize_initial_memory(
            data_entries,
            constants,
            code_labels,
            data_labels,
            code_offset=code_offset,
        )
        new_offset = len(_build_prologue(initial_memory))
        if new_offset == code_offset:
            break
        code_offset = new_offset
    prologue = _build_prologue(initial_memory)
    instructions = [
        _parse_instruction(
            entry.text,
            entry.line,
            constants,
            code_labels,
            data_labels,
            code_offset=code_offset,
        )
        for entry in code_entries
    ]
    return prologue + instructions


def _plan_layout(
    lines: Sequence[_SourceLine],
    constants: Dict[str, int],
) -> Tuple[List[_CodeEntry], List[_DataEntry], Dict[str, int], Dict[str, int]]:
    code_entries: List[_CodeEntry] = []
    data_entries: List[_DataEntry] = []
    code_labels: Dict[str, int] = {}
    data_labels: Dict[str, int] = {}
    pending_labels: List[Tuple[str, _SourceLine]] = []
    allocated_addresses: Dict[int, _SourceLine] = {}
    data_cursor = 0

    for line in lines:
        label, remainder = _split_label(line.text)
        text = remainder.strip() if label is not None else line.text.strip()
        if not text:
            if label is not None:
                pending_labels.append((label, line))
            continue

        labels = list(pending_labels)
        pending_labels = []
        if label is not None:
            labels.append((label, line))

        token = _first_token(text)
        upper_token = token.upper() if token is not None else ""
        if upper_token == "ORG":
            if labels:
                raise AssemblerError(f"{line.location}: labels are not allowed on ORG")
            operand = _require_operand(text, line, "ORG")
            data_cursor = _resolve_constant_token(operand, constants, line)
            continue

        if upper_token == "DATA":
            values = _parse_data_tokens(text, line)
            start_address = data_cursor
            addresses = tuple(start_address + offset for offset in range(len(values)))
            for addr in addresses:
                if addr in allocated_addresses:
                    previous = allocated_addresses[addr]
                    raise AssemblerError(
                        f"{line.location}: DATA overlaps address {addr} already initialized at {previous.location}"
                    )
                allocated_addresses[addr] = line
            for name, source_line in labels:
                _register_symbol(
                    name,
                    start_address,
                    source_line,
                    constants,
                    code_labels,
                    data_labels,
                    data_labels,
                )
            data_entries.append(_DataEntry(tokens=tuple(values), addresses=addresses, line=line))
            data_cursor = start_address + len(values)
            continue

        for name, source_line in labels:
            _register_symbol(
                name,
                len(code_entries),
                source_line,
                constants,
                code_labels,
                data_labels,
                code_labels,
            )
        code_entries.append(_CodeEntry(text=text, line=line))

    if pending_labels:
        dangling = ", ".join(name for name, _ in pending_labels)
        line = pending_labels[-1][1]
        raise AssemblerError(f"{line.location}: dangling label(s) without statement: {dangling}")

    return code_entries, data_entries, code_labels, data_labels


def _parse_instruction(
    text: str,
    line: _SourceLine,
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    *,
    code_offset: int,
) -> Instruction:
    parts = text.split(None, 1)
    opcode = parts[0].upper()
    operand_text = parts[1].strip() if len(parts) > 1 else None

    if opcode not in _ALL_OPS:
        raise AssemblerError(f"{line.location}: unknown opcode or undefined macro '{opcode}'")

    if opcode in _NO_OPERAND_OPS:
        if operand_text is not None:
            raise AssemblerError(f"{line.location}: opcode '{opcode}' takes no operand")
        return Instruction(opcode)

    if opcode in _VALUE_OPERAND_OPS:
        if operand_text is None:
            raise AssemblerError(f"{line.location}: opcode '{opcode}' requires an integer operand")
        return Instruction(
            opcode,
            _resolve_value_token(
                operand_text,
                line,
                constants,
                code_labels,
                data_labels,
                code_offset=code_offset,
            ),
        )

    if opcode in _TARGET_OPERAND_OPS:
        if operand_text is None:
            raise AssemblerError(f"{line.location}: opcode '{opcode}' requires a target operand")
        return Instruction(
            opcode,
            _resolve_target_token(
                operand_text,
                line,
                constants,
                code_labels,
                data_labels,
                code_offset=code_offset,
            ),
        )

    if operand_text is None:
        raise AssemblerError(f"{line.location}: opcode '{opcode}' requires three targets")
    return Instruction(
        opcode,
        _parse_br3(
            operand_text,
            line,
            constants,
            code_labels,
            data_labels,
            code_offset=code_offset,
        ),
    )


def _materialize_initial_memory(
    data_entries: Sequence[_DataEntry],
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    *,
    code_offset: int,
) -> Dict[int, int]:
    initial_memory: Dict[int, int] = {}
    for entry in data_entries:
        for address, token in zip(entry.addresses, entry.tokens):
            value = _resolve_value_token(
                token,
                entry.line,
                constants,
                code_labels,
                data_labels,
                code_offset=code_offset,
            )
            if value != 0:
                initial_memory[address] = value
    return initial_memory


def _build_prologue(initial_memory: Dict[int, int]) -> List[Instruction]:
    prologue: List[Instruction] = []
    for address in sorted(initial_memory):
        prologue.extend(
            [
                Instruction(Op.PUSH, address),
                Instruction(Op.PUSH, initial_memory[address]),
                Instruction(Op.STORE),
            ]
        )
    return prologue


def _parse_data_tokens(text: str, line: _SourceLine) -> List[str]:
    operand = _require_operand(text, line, "DATA")
    parts = [part.strip() for part in operand.split(",")]
    if not parts or any(not part for part in parts):
        raise AssemblerError(f"{line.location}: DATA requires one or more comma-separated values")
    return parts


def _parse_br3(
    text: str,
    line: _SourceLine,
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    *,
    code_offset: int,
) -> Tuple[int, int, int]:
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3 or any(not part for part in parts):
        raise AssemblerError(f"{line.location}: opcode 'BR3' requires three comma-separated targets")
    return tuple(
        _resolve_target_token(
            part,
            line,
            constants,
            code_labels,
            data_labels,
            code_offset=code_offset,
        )
        for part in parts
    )  # type: ignore[return-value]


def _resolve_value_token(
    token: str,
    line: _SourceLine,
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    *,
    code_offset: int,
) -> int:
    if token in constants:
        return constants[token]
    if token in data_labels:
        return data_labels[token]
    if token in code_labels:
        return code_labels[token] + code_offset
    try:
        return int(token)
    except ValueError as exc:
        raise AssemblerError(f"{line.location}: unknown symbol '{token}'") from exc


def _resolve_target_token(
    token: str,
    line: _SourceLine,
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    *,
    code_offset: int,
) -> int:
    if token in data_labels:
        raise AssemblerError(f"{line.location}: target '{token}' refers to data, not code")
    if token in code_labels:
        return code_labels[token] + code_offset
    try:
        return _resolve_constant_token(token, constants, line) + code_offset
    except AssemblerError as exc:
        raise AssemblerError(f"{line.location}: opcode requires a valid target") from exc


def _resolve_constant_token(token: str, constants: Dict[str, int], line: _SourceLine) -> int:
    if token in constants:
        return constants[token]
    try:
        return int(token)
    except ValueError as exc:
        raise AssemblerError(f"{line.location}: expected integer or DEF name, got '{token}'") from exc


def _resolve_include_path(text: str, line: _SourceLine) -> Path:
    match = _INCLUDE_RE.match(text)
    if match is None:
        raise AssemblerError(f"{line.location}: INCLUDE requires a quoted relative path")
    if line.base_dir is None:
        raise AssemblerError(f"{line.location}: INCLUDE requires file context or base_dir")
    return (line.base_dir / match.group("path")).resolve()


def _register_symbol(
    name: str,
    value: int,
    line: _SourceLine,
    constants: Dict[str, int],
    code_labels: Dict[str, int],
    data_labels: Dict[str, int],
    target: Dict[str, int],
) -> None:
    _require_name(name, line, "label")
    if name in constants or name in code_labels or name in data_labels:
        raise AssemblerError(f"{line.location}: duplicate label '{name}'")
    target[name] = value


def _require_name(name: str, line: _SourceLine, kind: str) -> None:
    if _NAME_RE.match(name) is None:
        raise AssemblerError(f"{line.location}: invalid {kind} name '{name}'")


def _require_operand(text: str, line: _SourceLine, keyword: str) -> str:
    parts = text.split(None, 1)
    if len(parts) != 2 or not parts[1].strip():
        raise AssemblerError(f"{line.location}: {keyword} requires an operand")
    return parts[1].strip()


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


def _first_token(text: str) -> str | None:
    parts = text.split(None, 1)
    if not parts:
        return None
    return parts[0]
