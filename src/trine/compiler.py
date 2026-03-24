"""Compiler for a minimal C-like Trine source language.

The language is intentionally small:

- functions with `fn name(args) { ... }`
- integers, variables, function calls, and arithmetic expressions
- comparison expressions that produce `0` or `1`
- statements: `let`, assignment, `if`, `while`, `print`, `return`

Compiled output is assembly text for the current Trine VM ISA. The generated
assembly is self-contained and targets the current `CALL` / `RET` plus
memory-backed frame convention.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, List, Optional, Sequence

from .assembler import assemble, assemble_image
from .vm import Instruction, ProgramImage, TernaryVM


_KEYWORDS = {"fn", "let", "if", "else", "while", "return", "print"}
_TOKEN_RE = re.compile(
    r"""
    (?P<SPACE>\s+)
  | (?P<COMMENT>//[^\n]*)
  | (?P<NUMBER>\d+)
  | (?P<OP>==|!=|<=|>=|[+\-*/%<>=(),;{}])
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<MISMATCH>.)
    """,
    re.VERBOSE,
)

_RUNTIME_DEFS = [
    "DEF RT_TMP0 -4",
    "DEF RT_TMP1 -5",
    "DEF RT_FP -8",
    "DEF RT_FRAME_TOP -9",
    "DEF RT_FRAME_BASE -32",
]


class CompileError(ValueError):
    """Raised when Trine high-level source cannot be compiled."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    line: int
    column: int
    source: str

    @property
    def location(self) -> str:
        return f"{self.source}:{self.line}:{self.column}"


@dataclass(frozen=True)
class _Program:
    functions: Sequence["_Function"]


@dataclass(frozen=True)
class _Function:
    name: str
    params: Sequence[str]
    body: Sequence["_Stmt"]
    token: _Token


class _Stmt:
    pass


@dataclass(frozen=True)
class _Let(_Stmt):
    name: str
    expr: "_Expr"
    token: _Token


@dataclass(frozen=True)
class _Assign(_Stmt):
    name: str
    expr: "_Expr"
    token: _Token


@dataclass(frozen=True)
class _If(_Stmt):
    condition: "_Expr"
    then_body: Sequence["_Stmt"]
    else_body: Sequence["_Stmt"]
    token: _Token


@dataclass(frozen=True)
class _While(_Stmt):
    condition: "_Expr"
    body: Sequence["_Stmt"]
    token: _Token


@dataclass(frozen=True)
class _Print(_Stmt):
    expr: "_Expr"
    token: _Token


@dataclass(frozen=True)
class _Return(_Stmt):
    expr: Optional["_Expr"]
    token: _Token


@dataclass(frozen=True)
class _ExprStmt(_Stmt):
    expr: "_Expr"
    token: _Token


class _Expr:
    pass


@dataclass(frozen=True)
class _Int(_Expr):
    value: int
    token: _Token


@dataclass(frozen=True)
class _Var(_Expr):
    name: str
    token: _Token


@dataclass(frozen=True)
class _Call(_Expr):
    name: str
    args: Sequence["_Expr"]
    token: _Token


@dataclass(frozen=True)
class _Unary(_Expr):
    op: str
    expr: _Expr
    token: _Token


@dataclass(frozen=True)
class _Binary(_Expr):
    left: _Expr
    op: str
    right: _Expr
    token: _Token


def compile_source(source: str, *, source_name: str = "<string>") -> str:
    """Compile high-level Trine source into assembly text."""
    program = _Parser(_tokenize(source, source_name)).parse_program()
    return _Compiler(program, source_name=source_name).render()


def compile_file(path: str | Path) -> str:
    file_path = Path(path)
    return compile_source(file_path.read_text(encoding="utf-8"), source_name=str(file_path))


def compile_program(source: str, *, source_name: str = "<string>") -> List[Instruction]:
    return assemble(compile_source(source, source_name=source_name))


def compile_image(source: str, *, source_name: str = "<string>") -> ProgramImage:
    return assemble_image(compile_source(source, source_name=source_name))


def compile_file_program(path: str | Path) -> List[Instruction]:
    file_path = Path(path)
    return compile_program(
        file_path.read_text(encoding="utf-8"),
        source_name=str(file_path),
    )


def compile_file_image(path: str | Path) -> ProgramImage:
    file_path = Path(path)
    return compile_image(
        file_path.read_text(encoding="utf-8"),
        source_name=str(file_path),
    )


def _tokenize(source: str, source_name: str) -> List[_Token]:
    tokens: List[_Token] = []
    pos = 0
    line = 1
    column = 1
    while pos < len(source):
        match = _TOKEN_RE.match(source, pos)
        if match is None:
            raise CompileError(f"{source_name}:{line}:{column}: invalid token")
        text = match.group(0)
        kind = match.lastgroup or "MISMATCH"
        if kind == "MISMATCH":
            raise CompileError(f"{source_name}:{line}:{column}: unexpected character '{text}'")
        if kind not in {"SPACE", "COMMENT"}:
            token_kind = text.upper() if kind == "IDENT" and text in _KEYWORDS else kind
            tokens.append(_Token(token_kind, text, line, column, source_name))
        for ch in text:
            if ch == "\n":
                line += 1
                column = 1
            else:
                column += 1
        pos = match.end()
    tokens.append(_Token("EOF", "", line, column, source_name))
    return tokens


class _Parser:
    def __init__(self, tokens: Sequence[_Token]) -> None:
        self.tokens = list(tokens)
        self.index = 0

    def parse_program(self) -> _Program:
        functions: List[_Function] = []
        while not self._at("EOF"):
            functions.append(self._parse_function())
        return _Program(functions=functions)

    def _parse_function(self) -> _Function:
        token = self._expect("FN", "expected 'fn'")
        name = self._expect("IDENT", "expected function name")
        self._expect_value("(", "expected '(' after function name")
        params: List[str] = []
        if not self._at_value(")"):
            while True:
                params.append(self._expect("IDENT", "expected parameter name").value)
                if not self._match_value(","):
                    break
        self._expect_value(")", "expected ')' after parameters")
        body = self._parse_block()
        return _Function(name=name.value, params=params, body=body, token=token)

    def _parse_block(self) -> List[_Stmt]:
        self._expect_value("{", "expected '{'")
        body: List[_Stmt] = []
        while not self._at_value("}"):
            if self._at("EOF"):
                token = self._peek()
                raise CompileError(f"{token.location}: expected '}}'")
            body.append(self._parse_statement())
        self._expect_value("}", "expected '}'")
        return body

    def _parse_statement(self) -> _Stmt:
        token = self._peek()
        if token.kind == "LET":
            self._advance()
            name = self._expect("IDENT", "expected variable name after 'let'")
            self._expect_value("=", "expected '=' after variable name")
            expr = self._parse_expression()
            self._expect_value(";", "expected ';' after declaration")
            return _Let(name=name.value, expr=expr, token=token)
        if token.kind == "IF":
            self._advance()
            self._expect_value("(", "expected '(' after 'if'")
            condition = self._parse_expression()
            self._expect_value(")", "expected ')' after if condition")
            then_body = self._parse_block()
            else_body: List[_Stmt] = []
            if self._match("ELSE"):
                else_body = self._parse_block()
            return _If(condition=condition, then_body=then_body, else_body=else_body, token=token)
        if token.kind == "WHILE":
            self._advance()
            self._expect_value("(", "expected '(' after 'while'")
            condition = self._parse_expression()
            self._expect_value(")", "expected ')' after while condition")
            body = self._parse_block()
            return _While(condition=condition, body=body, token=token)
        if token.kind == "PRINT":
            self._advance()
            expr = self._parse_expression()
            self._expect_value(";", "expected ';' after print")
            return _Print(expr=expr, token=token)
        if token.kind == "RETURN":
            self._advance()
            if self._at_value(";"):
                self._advance()
                return _Return(expr=None, token=token)
            expr = self._parse_expression()
            self._expect_value(";", "expected ';' after return")
            return _Return(expr=expr, token=token)
        if token.kind == "IDENT" and self._peek(1).value == "=":
            name = self._advance()
            self._expect_value("=", "expected '=' in assignment")
            expr = self._parse_expression()
            self._expect_value(";", "expected ';' after assignment")
            return _Assign(name=name.value, expr=expr, token=name)
        expr = self._parse_expression()
        self._expect_value(";", "expected ';' after expression")
        return _ExprStmt(expr=expr, token=token)

    def _parse_expression(self) -> _Expr:
        return self._parse_comparison()

    def _parse_comparison(self) -> _Expr:
        expr = self._parse_additive()
        if self._at_value("==", "!=", "<", "<=", ">", ">="):
            op = self._advance()
            right = self._parse_additive()
            expr = _Binary(expr, op.value, right, op)
            if self._at_value("==", "!=", "<", "<=", ">", ">="):
                token = self._peek()
                raise CompileError(f"{token.location}: chained comparisons are not supported")
        return expr

    def _parse_additive(self) -> _Expr:
        expr = self._parse_multiplicative()
        while self._at_value("+", "-"):
            op = self._advance()
            right = self._parse_multiplicative()
            expr = _Binary(expr, op.value, right, op)
        return expr

    def _parse_multiplicative(self) -> _Expr:
        expr = self._parse_unary()
        while self._at_value("*", "/", "%"):
            op = self._advance()
            right = self._parse_unary()
            expr = _Binary(expr, op.value, right, op)
        return expr

    def _parse_unary(self) -> _Expr:
        if self._at_value("-"):
            op = self._advance()
            return _Unary(op.value, self._parse_unary(), op)
        return self._parse_primary()

    def _parse_primary(self) -> _Expr:
        token = self._peek()
        if token.kind == "NUMBER":
            self._advance()
            return _Int(value=int(token.value), token=token)
        if token.kind == "IDENT":
            self._advance()
            if self._match_value("("):
                args: List[_Expr] = []
                if not self._at_value(")"):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match_value(","):
                            break
                self._expect_value(")", "expected ')' after call arguments")
                return _Call(name=token.value, args=args, token=token)
            return _Var(name=token.value, token=token)
        if self._match_value("("):
            expr = self._parse_expression()
            self._expect_value(")", "expected ')' after expression")
            return expr
        raise CompileError(f"{token.location}: expected expression")

    def _peek(self, offset: int = 0) -> _Token:
        index = min(self.index + offset, len(self.tokens) - 1)
        return self.tokens[index]

    def _advance(self) -> _Token:
        token = self._peek()
        self.index += 1
        return token

    def _at(self, kind: str) -> bool:
        return self._peek().kind == kind

    def _match(self, kind: str) -> bool:
        if self._at(kind):
            self._advance()
            return True
        return False

    def _at_value(self, *values: str) -> bool:
        return self._peek().value in values

    def _match_value(self, *values: str) -> bool:
        if self._at_value(*values):
            self._advance()
            return True
        return False

    def _expect(self, kind: str, message: str) -> _Token:
        token = self._peek()
        if token.kind != kind:
            raise CompileError(f"{token.location}: {message}")
        return self._advance()

    def _expect_value(self, value: str, message: str) -> _Token:
        token = self._peek()
        if token.value != value:
            raise CompileError(f"{token.location}: {message}")
        return self._advance()


class _Compiler:
    def __init__(self, program: _Program, *, source_name: str) -> None:
        self.program = program
        self.source_name = source_name
        self.lines: List[str] = []
        self.label_counter = 0
        self.functions = self._index_functions(program.functions)

    def render(self) -> str:
        main = self.functions.get("main")
        if main is None:
            raise CompileError(f"{self.source_name}: missing required function 'main'")
        if main["function"].params:
            token = main["function"].token
            raise CompileError(f"{token.location}: main must take no parameters")

        self.lines.extend(
            [
                "; Trine compiler output",
                "; compiled functions return a single integer; missing returns default to 0",
                "",
            ]
        )
        self.lines.extend(_RUNTIME_DEFS)
        self.lines.extend(["", "PUSH 0", "PUSH RT_FP", "SWAP", "STORE"])
        self.lines.extend(["PUSH RT_FRAME_BASE", "PUSH RT_FRAME_TOP", "SWAP", "STORE"])
        self.lines.extend(["CALL fn_main", "HALT", ""])

        for name, data in self.functions.items():
            self._emit_function(name, data["function"], data["locals"])

        return "\n".join(self.lines).rstrip() + "\n"

    def _index_functions(self, functions: Sequence[_Function]) -> dict[str, dict[str, object]]:
        indexed: dict[str, dict[str, object]] = {}
        for function in functions:
            if function.name in indexed:
                raise CompileError(
                    f"{function.token.location}: duplicate function '{function.name}'"
                )
            locals_map = self._collect_locals(function)
            indexed[function.name] = {
                "function": function,
                "locals": locals_map,
            }
        return indexed

    def _collect_locals(self, function: _Function) -> dict[str, int]:
        env = {name: index for index, name in enumerate(function.params)}
        next_slot = len(function.params)

        def visit(stmts: Iterable[_Stmt]) -> None:
            nonlocal next_slot
            for stmt in stmts:
                if isinstance(stmt, _Let):
                    if stmt.name in env:
                        raise CompileError(
                            f"{stmt.token.location}: duplicate local or parameter '{stmt.name}'"
                        )
                    env[stmt.name] = next_slot
                    next_slot += 1
                elif isinstance(stmt, _If):
                    visit(stmt.then_body)
                    visit(stmt.else_body)
                elif isinstance(stmt, _While):
                    visit(stmt.body)

        visit(function.body)
        return env

    def _emit_function(self, name: str, function: _Function, locals_map: dict[str, int]) -> None:
        slot_count = len(locals_map)
        self.lines.extend([f"fn_{name}:", f"; fn {name}"])
        self._emit_enter(slot_count)
        for param_name in reversed(function.params):
            self._emit_local_store(locals_map[param_name])
        for stmt in function.body:
            self._emit_stmt(stmt, function, locals_map, slot_count)
        self.lines.extend(["PUSH 0"])
        self._emit_leave(slot_count)
        self.lines.extend(["RET", ""])

    def _emit_stmt(
        self,
        stmt: _Stmt,
        function: _Function,
        locals_map: dict[str, int],
        slot_count: int,
    ) -> None:
        if isinstance(stmt, _Let):
            self._emit_expr(stmt.expr, function, locals_map)
            self._emit_local_store(locals_map[stmt.name])
            return
        if isinstance(stmt, _Assign):
            slot = self._require_local(stmt.name, stmt.token, locals_map)
            self._emit_expr(stmt.expr, function, locals_map)
            self._emit_local_store(slot)
            return
        if isinstance(stmt, _Print):
            self._emit_expr(stmt.expr, function, locals_map)
            self.lines.append("PRINT")
            return
        if isinstance(stmt, _Return):
            if stmt.expr is None:
                self.lines.append("PUSH 0")
            else:
                self._emit_expr(stmt.expr, function, locals_map)
            self._emit_leave(slot_count)
            self.lines.append("RET")
            return
        if isinstance(stmt, _ExprStmt):
            self._emit_expr(stmt.expr, function, locals_map)
            self.lines.append("POP")
            return
        if isinstance(stmt, _If):
            else_label = self._new_label("else")
            end_label = self._new_label("ifend")
            self._emit_expr(stmt.condition, function, locals_map)
            self.lines.append(f"JZ {else_label}")
            for inner in stmt.then_body:
                self._emit_stmt(inner, function, locals_map, slot_count)
            if stmt.else_body:
                self.lines.append(f"JMP {end_label}")
            self.lines.append(f"{else_label}:")
            for inner in stmt.else_body:
                self._emit_stmt(inner, function, locals_map, slot_count)
            if stmt.else_body:
                self.lines.append(f"{end_label}:")
            return
        if isinstance(stmt, _While):
            start_label = self._new_label("while")
            end_label = self._new_label("while_end")
            self.lines.append(f"{start_label}:")
            self._emit_expr(stmt.condition, function, locals_map)
            self.lines.append(f"JZ {end_label}")
            for inner in stmt.body:
                self._emit_stmt(inner, function, locals_map, slot_count)
            self.lines.append(f"JMP {start_label}")
            self.lines.append(f"{end_label}:")
            return
        raise AssertionError(f"unsupported statement: {stmt!r}")

    def _emit_expr(
        self,
        expr: _Expr,
        function: _Function,
        locals_map: dict[str, int],
    ) -> None:
        if isinstance(expr, _Int):
            self.lines.append(f"PUSH {expr.value}")
            return
        if isinstance(expr, _Var):
            slot = self._require_local(expr.name, expr.token, locals_map)
            self._emit_local_load(slot)
            return
        if isinstance(expr, _Call):
            target = self.functions.get(expr.name)
            if target is None:
                raise CompileError(f"{expr.token.location}: unknown function '{expr.name}'")
            expected = len(target["function"].params)  # type: ignore[index]
            if len(expr.args) != expected:
                raise CompileError(
                    f"{expr.token.location}: function '{expr.name}' expects {expected} args, got {len(expr.args)}"
                )
            for arg in expr.args:
                self._emit_expr(arg, function, locals_map)
            self.lines.append(f"CALL fn_{expr.name}")
            return
        if isinstance(expr, _Unary):
            self._emit_expr(expr.expr, function, locals_map)
            if expr.op == "-":
                self.lines.append("NEG")
                return
            raise AssertionError(f"unsupported unary op: {expr.op}")
        if isinstance(expr, _Binary):
            self._emit_expr(expr.left, function, locals_map)
            self._emit_expr(expr.right, function, locals_map)
            if expr.op == "+":
                self.lines.append("ADD")
                return
            if expr.op == "-":
                self.lines.append("SUB")
                return
            if expr.op == "*":
                self.lines.append("MUL")
                return
            if expr.op == "/":
                self.lines.append("DIV")
                return
            if expr.op == "%":
                self.lines.append("MOD")
                return
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                self._emit_bool_from_cmp(expr.op)
                return
            raise AssertionError(f"unsupported binary op: {expr.op}")
        raise AssertionError(f"unsupported expression: {expr!r}")

    def _emit_bool_from_cmp(self, op: str) -> None:
        true_label = self._new_label("cmp_true")
        false_label = self._new_label("cmp_false")
        end_label = self._new_label("cmp_end")
        branch_map = {
            "==": (false_label, true_label, false_label),
            "!=": (true_label, false_label, true_label),
            "<": (true_label, false_label, false_label),
            "<=": (true_label, true_label, false_label),
            ">": (false_label, false_label, true_label),
            ">=": (false_label, true_label, true_label),
        }
        neg_target, zero_target, pos_target = branch_map[op]
        self.lines.append("CMP")
        self.lines.append(f"BR3 {neg_target}, {zero_target}, {pos_target}")
        self.lines.append(f"{false_label}:")
        self.lines.append("PUSH 0")
        self.lines.append(f"JMP {end_label}")
        self.lines.append(f"{true_label}:")
        self.lines.append("PUSH 1")
        self.lines.append(f"{end_label}:")

    def _emit_enter(self, slot_count: int) -> None:
        self._emit_load_cell("RT_FP")
        self._emit_store_cell("RT_TMP0")
        self._emit_load_cell("RT_FRAME_TOP")
        self.lines.append("DUP")
        self._emit_store_cell("RT_FP")
        self.lines.append(f"PUSH {slot_count}")
        self.lines.append("SUB")
        self.lines.append("DUP")
        self._emit_store_cell("RT_TMP1")
        self._emit_load_cell("RT_TMP0")
        self.lines.append("STORE")
        self._emit_load_cell("RT_TMP1")
        self.lines.append("DEC")
        self._emit_store_cell("RT_FRAME_TOP")

    def _emit_leave(self, slot_count: int) -> None:
        self._emit_load_cell("RT_FP")
        self.lines.append("DUP")
        self._emit_store_cell("RT_TMP0")
        self.lines.append(f"PUSH {slot_count}")
        self.lines.append("SUB")
        self.lines.append("LOAD")
        self._emit_store_cell("RT_FP")
        self._emit_load_cell("RT_TMP0")
        self._emit_store_cell("RT_FRAME_TOP")

    def _emit_local_load(self, slot: int) -> None:
        self._emit_load_cell("RT_FP")
        self.lines.append(f"PUSH {slot}")
        self.lines.append("SUB")
        self.lines.append("LOAD")

    def _emit_local_store(self, slot: int) -> None:
        self._emit_load_cell("RT_FP")
        self.lines.append(f"PUSH {slot}")
        self.lines.append("SUB")
        self.lines.append("SWAP")
        self.lines.append("STORE")

    def _emit_load_cell(self, name: str) -> None:
        self.lines.append(f"PUSH {name}")
        self.lines.append("LOAD")

    def _emit_store_cell(self, name: str) -> None:
        self.lines.append(f"PUSH {name}")
        self.lines.append("SWAP")
        self.lines.append("STORE")

    def _require_local(self, name: str, token: _Token, locals_map: dict[str, int]) -> int:
        if name not in locals_map:
            raise CompileError(f"{token.location}: unknown variable '{name}'")
        return locals_map[name]

    def _new_label(self, prefix: str) -> str:
        label = f"__{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Compile Trine high-level source")
    parser.add_argument("path", help="Path to a .tri source file")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Compile and execute the program instead of printing assembly",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.run:
        vm = TernaryVM(compile_file_program(args.path)).run()
        for line in vm.output:
            print(line)
        return 0

    print(compile_file(args.path), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
