"""Logical benchmark runner for the current Trine reference implementation.

The report focuses on deterministic machine-model metrics:

- `vm_steps`: instruction dispatch steps in `TernaryVM`
- `alu_ticks`: primitive tape/FSM work performed underneath composite helpers
- `composite_ops`: VM instructions implemented as host-side helpers or
  compositions over primitive machine runs

This is intentionally not a wall-clock performance benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .assembler import assemble_file
from .compiler import compile_file_program
from .vm import Instruction, Op, TernaryVM


@dataclass(frozen=True)
class BenchmarkRow:
    name: str
    result: str
    vm_steps: int
    alu_ticks: int
    composite_ops: int


@dataclass(frozen=True)
class DivisionScalingRow:
    dividend: int
    divisor: int
    quotient: int
    vm_steps: int
    alu_ticks: int
    composite_ops: int


def _examples_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "examples"


def _render_result(vm: TernaryVM) -> str:
    if vm.output:
        return ", ".join(item.split()[0] for item in vm.output)
    if vm.stack:
        return str(vm.stack)
    return "-"


def _run_case(name: str, program: List[Instruction]) -> BenchmarkRow:
    vm = TernaryVM(program).run()
    return BenchmarkRow(
        name=name,
        result=_render_result(vm),
        vm_steps=vm.step_count,
        alu_ticks=vm.alu_ticks,
        composite_ops=vm.composite_ops,
    )


def _unary_case(name: str, value: int, op: str) -> BenchmarkRow:
    return _run_case(
        name,
        [
            Instruction(Op.PUSH, value),
            Instruction(op),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ],
    )


def _binary_case(name: str, a: int, b: int, op: str) -> BenchmarkRow:
    return _run_case(
        name,
        [
            Instruction(Op.PUSH, a),
            Instruction(Op.PUSH, b),
            Instruction(op),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ],
    )


def _factorial_loop_program() -> List[Instruction]:
    return [
        Instruction(Op.PUSH, 6),
        Instruction(Op.PUSH, 1),
        Instruction(Op.OVER),
        Instruction(Op.JP, 5),
        Instruction(Op.JMP, 11),
        Instruction(Op.OVER),
        Instruction(Op.MUL),
        Instruction(Op.SWAP),
        Instruction(Op.DEC),
        Instruction(Op.SWAP),
        Instruction(Op.JMP, 2),
        Instruction(Op.SWAP),
        Instruction(Op.POP),
        Instruction(Op.PRINT),
        Instruction(Op.HALT),
    ]


def _fibonacci_program() -> List[Instruction]:
    program = [
        Instruction(Op.PUSH, 0),
        Instruction(Op.DUP),
        Instruction(Op.PRINT),
        Instruction(Op.PUSH, 1),
    ]
    for _ in range(7):
        program.extend(
            [
                Instruction(Op.DUP),
                Instruction(Op.PRINT),
                Instruction(Op.SWAP),
                Instruction(Op.OVER),
                Instruction(Op.ADD),
            ]
        )
    program.append(Instruction(Op.HALT))
    return program


def _powers_of_two_program() -> List[Instruction]:
    program = [
        Instruction(Op.PUSH, 1),
        Instruction(Op.DUP),
        Instruction(Op.PRINT),
    ]
    for _ in range(7):
        program.extend(
            [
                Instruction(Op.DUP),
                Instruction(Op.ADD),
                Instruction(Op.DUP),
                Instruction(Op.PRINT),
            ]
        )
    program.append(Instruction(Op.HALT))
    return program


def _call_ret_round_trip_program() -> List[Instruction]:
    return [
        Instruction(Op.CALL, 2),
        Instruction(Op.HALT),
        Instruction(Op.RET),
    ]


def benchmark_operations() -> List[BenchmarkRow]:
    """Representative per-operation VM metrics across the current ISA surface."""
    return [
        _unary_case("INC 13", 13, Op.INC),
        _unary_case("DEC 13", 13, Op.DEC),
        _unary_case("NEG -13", -13, Op.NEG),
        _binary_case("ADD 13 14", 13, 14, Op.ADD),
        _unary_case("ABS -13", -13, Op.ABS),
        _binary_case("SUB 13 14", 13, 14, Op.SUB),
        _binary_case("CMP 13 14", 13, 14, Op.CMP),
        _binary_case("MIN 13 -4", 13, -4, Op.MIN),
        _binary_case("MAX 13 -4", 13, -4, Op.MAX),
        _binary_case("CONS 4 4", 4, 4, Op.CONS),
        _binary_case("DIV -7 3", -7, 3, Op.DIV),
        _binary_case("MOD -7 3", -7, 3, Op.MOD),
        _binary_case("MUL 13 -4", 13, -4, Op.MUL),
        _unary_case("SHL 13", 13, Op.SHL),
        _unary_case("SHR 13", 13, Op.SHR),
        _unary_case("SGN -13", -13, Op.SGN),
    ]


def benchmark_programs() -> List[BenchmarkRow]:
    """Representative whole-program metrics."""
    examples = _examples_dir()
    return [
        _run_case("call_ret_round_trip", _call_ret_round_trip_program()),
        _run_case(
            "call_leaf",
            assemble_file(examples / "call_leaf.trine"),
        ),
        _run_case(
            "factorial_call_recursive",
            assemble_file(examples / "factorial_call.trine"),
        ),
        _run_case(
            "factorial_high_level_compiled",
            compile_file_program(examples / "factorial_high_level.tri"),
        ),
        _run_case(
            "sum_to_high_level_compiled",
            compile_file_program(examples / "sum_to_high_level.tri"),
        ),
        _run_case(
            "factorial_unrolled",
            assemble_file(examples / "factorial.trine"),
        ),
        _run_case("factorial_loop", _factorial_loop_program()),
        _run_case(
            "count_to_five_asm",
            assemble_file(examples / "count_to_five.trine"),
        ),
        _run_case(
            "memory_round_trip",
            [
                Instruction(Op.PUSH, 4),
                Instruction(Op.PUSH, 13),
                Instruction(Op.STORE),
                Instruction(Op.PUSH, 4),
                Instruction(Op.LOAD),
                Instruction(Op.PRINT),
                Instruction(Op.HALT),
            ],
        ),
        _run_case("fibonacci_8", _fibonacci_program()),
        _run_case("powers_of_two_8", _powers_of_two_program()),
    ]


def benchmark_division_scaling(
    dividends: Sequence[int] = (3, 9, 27, 81),
    divisor: int = 3,
) -> List[DivisionScalingRow]:
    """Show current `DIV` cost growth with larger quotients."""
    rows: List[DivisionScalingRow] = []
    for dividend in dividends:
        vm = TernaryVM(
            [
                Instruction(Op.PUSH, dividend),
                Instruction(Op.PUSH, divisor),
                Instruction(Op.DIV),
                Instruction(Op.PRINT),
                Instruction(Op.HALT),
            ]
        ).run()
        rows.append(
            DivisionScalingRow(
                dividend=dividend,
                divisor=divisor,
                quotient=int(vm.output[0].split()[0]),
                vm_steps=vm.step_count,
                alu_ticks=vm.alu_ticks,
                composite_ops=vm.composite_ops,
            )
        )
    return rows


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def render_benchmark_report() -> str:
    operation_rows = benchmark_operations()
    program_rows = benchmark_programs()
    division_rows = benchmark_division_scaling()

    sections = [
        "# Trine Benchmark Note",
        "",
        "Generated from `python -m trine.benchmarks`.",
        "",
        "These are deterministic machine-model metrics from the current Python",
        "reference implementation. They are not wall-clock benchmarks and should",
        "not be used to make runtime or hardware-efficiency claims.",
        "",
        "## Operation Snapshot",
        "",
        _table(
            ("Case", "Result", "VM Steps", "ALU Ticks", "Composite Ops"),
            (
                (row.name, row.result, row.vm_steps, row.alu_ticks, row.composite_ops)
                for row in operation_rows
            ),
        ),
        "",
        "## Program Snapshot",
        "",
        _table(
            ("Case", "Result", "VM Steps", "ALU Ticks", "Composite Ops"),
            (
                (row.name, row.result, row.vm_steps, row.alu_ticks, row.composite_ops)
                for row in program_rows
            ),
        ),
        "",
        "`CALL` and `RET` are composite control-flow instructions. They affect",
        "`composite_ops` but do not contribute to `alu_ticks` directly.",
        "",
        "## Division Cost Growth",
        "",
        _table(
            ("Case", "Quotient", "VM Steps", "ALU Ticks", "Composite Ops"),
            (
                (
                    f"DIV {row.dividend} {row.divisor}",
                    row.quotient,
                    row.vm_steps,
                    row.alu_ticks,
                    row.composite_ops,
                )
                for row in division_rows
            ),
        ),
        "",
        "`DIV` and `MOD` currently use repeated subtraction over absolute values,",
        "plus sign-fixup. In this reference model, their ALU tick cost therefore",
        "grows roughly linearly with quotient magnitude.",
    ]
    return "\n".join(sections)


def main() -> int:
    print(render_benchmark_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
