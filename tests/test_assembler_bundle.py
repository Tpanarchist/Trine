from pathlib import Path

import pytest

from trine import (
    AssemblerError,
    Instruction,
    Op,
    ProgramImage,
    TernaryVM,
    assemble,
    assemble_file,
    assemble_file_image,
    assemble_image,
)


def _ints(output: list[str]) -> list[int]:
    return [int(item.split()[0]) for item in output]


class TestProgramImage:
    def test_assemble_returns_lowered_list_for_data_source(self):
        program = assemble(
            """
            value: DATA 7
            PUSH value
            LOAD
            PRINT
            HALT
            """
        )
        assert isinstance(program, list)
        assert program[:3] == [
            Instruction(Op.PUSH, 0),
            Instruction(Op.PUSH, 7),
            Instruction(Op.STORE),
        ]

    def test_assemble_image_returns_program_image(self):
        image = assemble_image(
            """
            value: DATA 7
            PUSH value
            LOAD
            PRINT
            HALT
            """
        )
        assert isinstance(image, ProgramImage)
        assert image.initial_memory == {0: 7}
        assert image.instructions == [
            Instruction(Op.PUSH, 0),
            Instruction(Op.LOAD),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]

    def test_prologue_mode_and_image_mode_execute_identically_for_data(self):
        source = """
        values: DATA 4, -1
        PUSH values
        LOAD
        PRINT
        PUSH values
        INC
        LOAD
        PRINT
        HALT
        """
        vm_list = TernaryVM(assemble(source)).run()
        vm_image = TernaryVM(assemble_image(source)).run()
        assert _ints(vm_list.output) == [4, -1]
        assert vm_list.output == vm_image.output

    def test_program_image_reset_restores_initial_memory(self):
        image = assemble_image(
            """
            cell: DATA 13
            PUSH cell
            PUSH 0
            STORE
            HALT
            """
        )
        vm = TernaryVM(image)
        assert vm.memory == {0: 13}
        vm.run()
        assert vm.memory == {}
        vm.reset()
        assert vm.memory == {0: 13}

    def test_code_label_in_data_uses_fixed_point_prologue_offset(self):
        program = assemble(
            """
            flag: DATA 1
            ptr: DATA start
            start:
            PUSH ptr
            LOAD
            PRINT
            HALT
            """
        )
        assert program[:6] == [
            Instruction(Op.PUSH, 0),
            Instruction(Op.PUSH, 1),
            Instruction(Op.STORE),
            Instruction(Op.PUSH, 1),
            Instruction(Op.PUSH, 6),
            Instruction(Op.STORE),
        ]


class TestAssemblerDirectives:
    def test_def_substitutes_in_push_jump_org_and_data(self):
        source = """
        DEF BASE 10
        DEF EXIT 4
        ORG BASE
        table: DATA BASE, -1
        PUSH table
        PRINT
        JMP EXIT
        PUSH 99
        HALT
        """
        image = assemble_image(source)
        assert image.initial_memory == {10: 10, 11: -1}
        assert image.instructions[0] == Instruction(Op.PUSH, 10)
        assert image.instructions[2] == Instruction(Op.JMP, 4)
        assert _ints(TernaryVM(assemble(source)).run().output) == [10]
        assert _ints(TernaryVM(image).run().output) == [10]

    def test_include_resolution_works_for_file_and_base_dir(self, tmp_path: Path):
        helper = tmp_path / "helper.trine"
        helper.write_text("DEF VALUE 7\n", encoding="utf-8")
        main = tmp_path / "main.trine"
        main.write_text(
            'INCLUDE "helper.trine"\nPUSH VALUE\nPRINT\nHALT\n',
            encoding="utf-8",
        )

        vm_file = TernaryVM(assemble_file(main)).run()
        vm_string = TernaryVM(assemble(main.read_text(encoding="utf-8"), base_dir=tmp_path)).run()
        assert _ints(vm_file.output) == _ints(vm_string.output) == [7]

    def test_include_requires_base_dir_for_string_source(self):
        with pytest.raises(AssemblerError, match="base_dir"):
            assemble('INCLUDE "helper.trine"\nHALT\n')

    def test_include_cycle_detection(self, tmp_path: Path):
        a = tmp_path / "a.trine"
        b = tmp_path / "b.trine"
        a.write_text('INCLUDE "b.trine"\nHALT\n', encoding="utf-8")
        b.write_text('INCLUDE "a.trine"\nHALT\n', encoding="utf-8")
        with pytest.raises(AssemblerError, match="include cycle"):
            assemble_file(a)

    def test_duplicate_include_rejected(self, tmp_path: Path):
        helper = tmp_path / "helper.trine"
        helper.write_text("HALT\n", encoding="utf-8")
        main = tmp_path / "main.trine"
        main.write_text(
            'INCLUDE "helper.trine"\nINCLUDE "helper.trine"\nHALT\n',
            encoding="utf-8",
        )
        with pytest.raises(AssemblerError, match="duplicate include"):
            assemble_file(main)

    def test_duplicate_def_rejected(self):
        with pytest.raises(AssemblerError, match="duplicate DEF"):
            assemble(
                """
                DEF VALUE 1
                DEF VALUE 2
                HALT
                """
            )

    def test_duplicate_macro_rejected(self):
        with pytest.raises(AssemblerError, match="duplicate MACRO"):
            assemble(
                """
                MACRO HOLD
                HALT
                ENDMACRO
                MACRO HOLD
                HALT
                ENDMACRO
                HOLD
                """
            )

    def test_bad_macro_arity_rejected(self):
        with pytest.raises(AssemblerError, match="expects 1 args, got 2"):
            assemble(
                """
                MACRO EMIT value
                PUSH {value}
                PRINT
                ENDMACRO
                EMIT 1 2
                HALT
                """
            )

    def test_unknown_macro_reports_useful_error(self):
        with pytest.raises(AssemblerError, match="undefined macro"):
            assemble("MISSING_MACRO 1\nHALT\n")

    def test_invalid_org_and_data_are_rejected(self):
        with pytest.raises(AssemblerError, match="ORG requires an operand"):
            assemble("ORG")
        with pytest.raises(AssemblerError, match="expected integer or DEF name"):
            assemble("DEF BASE 10\nORG MISSING\nHALT\n")
        with pytest.raises(AssemblerError, match="DATA requires one or more comma-separated values"):
            assemble("DATA 1, , 2\nHALT\n")

    def test_data_overlap_is_rejected(self):
        with pytest.raises(AssemblerError, match="overlaps address"):
            assemble_image(
                """
                ORG 5
                first: DATA 1, 2
                ORG 6
                second: DATA 3
                HALT
                """
            )

    def test_nested_macro_definition_is_rejected(self):
        with pytest.raises(AssemblerError, match="nested MACRO"):
            assemble(
                """
                MACRO OUTER
                MACRO INNER
                HALT
                ENDMACRO
                ENDMACRO
                OUTER
                """
            )

    def test_macro_local_labels_do_not_collide(self):
        vm = TernaryVM(
            assemble(
                """
                MACRO SIGN_PRINT value
                PUSH {value}
                BR3 @neg, @zero, @pos
                @neg: PUSH -1
                JMP @done
                @zero: PUSH 0
                JMP @done
                @pos: PUSH 1
                @done: PRINT
                ENDMACRO

                SIGN_PRINT 5
                SIGN_PRINT -2
                HALT
                """
            )
        ).run()
        assert _ints(vm.output) == [1, -1]


class TestMemoryExamples:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("array_sum.trine", [6]),
            ("linked_list_walk.trine", [4, -1, 7]),
            ("state_table_fsm.trine", [1, 2, 2, 0]),
        ],
    )
    def test_examples_execute_in_list_and_image_modes(self, name: str, expected: list[int]):
        path = Path(__file__).resolve().parents[1] / "examples" / name
        vm_list = TernaryVM(assemble_file(path)).run()
        vm_image = TernaryVM(assemble_file_image(path)).run()
        assert _ints(vm_list.output) == expected
        assert vm_list.output == vm_image.output
