from pathlib import Path

import pytest

from trine import (
    CompileError,
    ProgramImage,
    TernaryVM,
    compile_file,
    compile_file_image,
    compile_file_program,
    compile_image,
    compile_program,
    compile_source,
)
from trine.benchmarks import benchmark_programs, render_benchmark_report


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _ints(output: list[str]) -> list[int]:
    return [int(item.split()[0]) for item in output]


class TestCompilerOutput:
    def test_compile_source_emits_self_contained_assembly(self):
        assembly = compile_source(
            """
            fn main() {
                print 1 + 2;
            }
            """
        )
        assert "DEF RT_FP -8" in assembly
        assert "CALL fn_main" in assembly
        assert "fn_main:" in assembly

    def test_compile_program_runs_recursive_factorial_example(self):
        vm = TernaryVM(compile_file_program(EXAMPLES_DIR / "factorial_high_level.tri")).run()
        assert _ints(vm.output) == [120]

    def test_compile_program_runs_while_loop_example(self):
        vm = TernaryVM(compile_file_program(EXAMPLES_DIR / "sum_to_high_level.tri")).run()
        assert _ints(vm.output) == [15]

    def test_compile_image_returns_program_image(self):
        image = compile_image(
            """
            fn main() {
                print 7;
            }
            """
        )
        assert isinstance(image, ProgramImage)
        assert image.initial_memory == {}
        assert _ints(TernaryVM(image).run().output) == [7]

    def test_compile_file_and_compile_file_image_execute_identically(self):
        program = compile_file_program(EXAMPLES_DIR / "factorial_high_level.tri")
        image = compile_file_image(EXAMPLES_DIR / "factorial_high_level.tri")
        vm_program = TernaryVM(program).run()
        vm_image = TernaryVM(image).run()
        assert vm_program.output == vm_image.output


class TestCompilerSemantics:
    def test_comparisons_produce_zero_or_one(self):
        vm = TernaryVM(
            compile_program(
                """
                fn main() {
                    print 1 < 2;
                    print 2 < 1;
                    print 2 == 2;
                    print 2 != 2;
                    print 2 >= 2;
                    print 1 <= 0;
                }
                """
            )
        ).run()
        assert _ints(vm.output) == [1, 0, 1, 0, 1, 0]

    def test_expression_statement_discards_function_result(self):
        vm = TernaryVM(
            compile_program(
                """
                fn tick() {
                    return 7;
                }

                fn main() {
                    tick();
                    print 1;
                }
                """
            )
        ).run()
        assert _ints(vm.output) == [1]

    def test_missing_return_defaults_to_zero(self):
        vm = TernaryVM(
            compile_program(
                """
                fn helper() {
                    let x = 4;
                }

                fn main() {
                    print helper();
                }
                """
            )
        ).run()
        assert _ints(vm.output) == [0]

    def test_return_without_value_defaults_to_zero(self):
        vm = TernaryVM(
            compile_program(
                """
                fn helper() {
                    return;
                }

                fn main() {
                    print helper();
                }
                """
            )
        ).run()
        assert _ints(vm.output) == [0]

    def test_local_assignment_and_parameter_spill_work(self):
        vm = TernaryVM(
            compile_program(
                """
                fn adjust(n) {
                    let acc = n + 1;
                    acc = acc + n;
                    return acc;
                }

                fn main() {
                    print adjust(4);
                }
                """
            )
        ).run()
        assert _ints(vm.output) == [9]


class TestCompilerErrors:
    def test_missing_main_rejected(self):
        with pytest.raises(CompileError, match="missing required function 'main'"):
            compile_source("fn helper() { return 1; }")

    def test_main_must_take_no_parameters(self):
        with pytest.raises(CompileError, match="main must take no parameters"):
            compile_source("fn main(x) { return x; }")

    def test_duplicate_function_rejected(self):
        with pytest.raises(CompileError, match="duplicate function 'main'"):
            compile_source(
                """
                fn main() { return 1; }
                fn main() { return 2; }
                """
            )

    def test_duplicate_local_rejected(self):
        with pytest.raises(CompileError, match="duplicate local or parameter 'x'"):
            compile_source(
                """
                fn main() {
                    let x = 1;
                    let x = 2;
                }
                """
            )

    def test_unknown_variable_rejected(self):
        with pytest.raises(CompileError, match="unknown variable 'x'"):
            compile_source(
                """
                fn main() {
                    print x;
                }
                """
            )

    def test_unknown_function_rejected(self):
        with pytest.raises(CompileError, match="unknown function 'missing'"):
            compile_source(
                """
                fn main() {
                    print missing();
                }
                """
            )

    def test_function_arity_mismatch_rejected(self):
        with pytest.raises(CompileError, match="expects 2 args, got 1"):
            compile_source(
                """
                fn add(a, b) {
                    return a + b;
                }

                fn main() {
                    print add(1);
                }
                """
            )

    def test_chained_comparison_rejected(self):
        with pytest.raises(CompileError, match="chained comparisons are not supported"):
            compile_source(
                """
                fn main() {
                    print 1 < 2 < 3;
                }
                """
            )

    def test_syntax_error_reports_location(self):
        with pytest.raises(CompileError, match=r"<string>:1:9: expected '\(' after function name"):
            compile_source("fn main { }")

    def test_compile_file_returns_assembly_text(self):
        assembly = compile_file(EXAMPLES_DIR / "factorial_high_level.tri")
        assert "fn_fact:" in assembly


class TestCompilerBenchmarks:
    def test_benchmarks_cover_compiled_programs(self):
        labels = {row.name for row in benchmark_programs()}
        assert {"factorial_high_level_compiled", "sum_to_high_level_compiled"} <= labels

    def test_benchmark_report_mentions_compiled_programs(self):
        report = render_benchmark_report()
        assert "factorial_high_level_compiled" in report
        assert "sum_to_high_level_compiled" in report
