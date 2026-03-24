from pathlib import Path

import pytest

from trine import (
    AssemblerError,
    Instruction,
    Op,
    TernaryVM,
    VMError,
    assemble,
    assemble_file,
    assemble_file_image,
)
from trine.benchmarks import benchmark_programs, render_benchmark_report


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _ints(output: list[str]) -> list[int]:
    return [int(item.split()[0]) for item in output]


class TestCallRetVM:
    def test_call_and_ret_round_trip(self):
        vm = TernaryVM(
            [
                Instruction(Op.CALL, 2),
                Instruction(Op.HALT),
                Instruction(Op.RET),
            ]
        ).run()
        assert vm.halted is True
        assert vm.step_count == 3
        assert vm.alu_ticks == 0
        assert vm.composite_ops == 2
        assert vm.return_stack == []

    def test_nested_calls_unwind_in_lifo_order(self):
        vm = TernaryVM(
            [
                Instruction(Op.CALL, 3),
                Instruction(Op.HALT),
                Instruction(Op.PUSH, 99),
                Instruction(Op.CALL, 5),
                Instruction(Op.RET),
                Instruction(Op.PUSH, 7),
                Instruction(Op.PRINT),
                Instruction(Op.RET),
            ]
        ).run()
        assert _ints(vm.output) == [7]
        assert vm.return_stack == []

    def test_ret_underflow_raises(self):
        with pytest.raises(VMError, match="return stack underflow at pc=0"):
            TernaryVM([Instruction(Op.RET)]).run()

    def test_reset_clears_return_stack(self):
        vm = TernaryVM(
            [
                Instruction(Op.CALL, 2),
                Instruction(Op.HALT),
                Instruction(Op.RET),
            ]
        )
        vm.step()
        assert vm.return_stack == [1]
        vm.reset()
        assert vm.return_stack == []


class TestCallRetAssembler:
    def test_call_accepts_numeric_targets(self):
        program = assemble("CALL 2\nRET\nHALT\n")
        assert program[0] == Instruction(Op.CALL, 2)
        assert program[1] == Instruction(Op.RET)

    def test_call_accepts_labels(self):
        program = assemble(
            """
            CALL done
            PUSH 99
            done: RET
            """
        )
        assert program[0] == Instruction(Op.CALL, 2)
        assert program[2] == Instruction(Op.RET)

    def test_ret_rejects_operands(self):
        with pytest.raises(AssemblerError, match="opcode 'RET' takes no operand"):
            assemble("RET 1\n")


class TestCallingConvention:
    def test_init_frames_sets_runtime_defaults(self):
        vm = TernaryVM(
            assemble(
                """
                INCLUDE "lib/runtime.trine"
                INCLUDE "lib/memory.trine"
                INCLUDE "lib/frames.trine"
                INIT_FRAMES
                LOAD_CELL RT_FP
                PRINT
                LOAD_CELL RT_FRAME_TOP
                PRINT
                HALT
                """,
                base_dir=EXAMPLES_DIR,
            )
        ).run()
        assert _ints(vm.output) == [0, -32]

    def test_local_store_and_load_use_expected_frame_slots(self):
        vm = TernaryVM(
            assemble(
                """
                INCLUDE "lib/runtime.trine"
                INCLUDE "lib/memory.trine"
                INCLUDE "lib/frames.trine"
                INIT_FRAMES
                ENTER 2
                PUSH 9
                LOCAL_STORE 0
                PUSH 4
                LOCAL_STORE 1
                LOAD_CELL RT_FP
                PRINT
                LOCAL_LOAD 1
                PRINT
                LOCAL_LOAD 0
                PRINT
                LEAVE 2
                HALT
                """,
                base_dir=EXAMPLES_DIR,
            )
        ).run()
        assert _ints(vm.output) == [-32, 4, 9]
        assert vm.memory[-32] == 9
        assert vm.memory[-33] == 4
        assert vm.memory.get(-34, 0) == 0

    def test_enter_and_leave_restore_parent_frame_across_nested_calls(self):
        vm = TernaryVM(
            assemble(
                """
                INCLUDE "lib/runtime.trine"
                INCLUDE "lib/memory.trine"
                INCLUDE "lib/frames.trine"

                INIT_FRAMES
                CALL outer
                LOAD_CELL RT_FP
                PRINT
                LOAD_CELL RT_FRAME_TOP
                PRINT
                HALT

                outer:
                ENTER 1
                PUSH 10
                LOCAL_STORE 0
                CALL inner
                LOCAL_LOAD 0
                PRINT
                LEAVE 1
                RET

                inner:
                ENTER 1
                PUSH 20
                LOCAL_STORE 0
                LOCAL_LOAD 0
                PRINT
                LEAVE 1
                RET
                """,
                base_dir=EXAMPLES_DIR,
            )
        ).run()
        assert _ints(vm.output) == [20, 10, 0, -32]
        assert vm.return_stack == []


class TestSubroutineExamples:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("call_leaf.trine", [9]),
            ("factorial_call.trine", [120]),
        ],
    )
    def test_examples_execute_in_list_and_image_modes(self, name: str, expected: list[int]):
        path = EXAMPLES_DIR / name
        vm_list = TernaryVM(assemble_file(path)).run()
        vm_image = TernaryVM(assemble_file_image(path)).run()
        assert _ints(vm_list.output) == expected
        assert vm_list.output == vm_image.output
        assert vm_list.return_stack == []
        assert vm_image.return_stack == []

    def test_recursive_factorial_uses_frames_and_returns_one_value(self):
        vm = TernaryVM(assemble_file(EXAMPLES_DIR / "factorial_call.trine")).run()
        assert _ints(vm.output) == [120]
        assert vm.memory.get(-9) == -32
        assert vm.memory.get(-8, 0) == 0
        assert vm.return_stack == []


class TestSubroutineBenchmarks:
    def test_program_benchmarks_cover_call_and_recursion(self):
        labels = {row.name for row in benchmark_programs()}
        assert {"call_ret_round_trip", "call_leaf", "factorial_call_recursive"} <= labels

    def test_render_benchmark_report_mentions_subroutine_costs(self):
        report = render_benchmark_report()
        assert "call_ret_round_trip" in report
        assert "factorial_call_recursive" in report
        assert "`CALL` and `RET` are composite control-flow instructions." in report
