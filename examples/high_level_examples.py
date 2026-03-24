from pathlib import Path

from trine import TernaryVM, compile_file, compile_file_program


EXAMPLES = [
    ("factorial_high_level.tri", [120]),
    ("sum_to_high_level.tri", [15]),
]


def _ints(output: list[str]) -> list[int]:
    return [int(item.split()[0]) for item in output]


def main() -> int:
    examples_dir = Path(__file__).resolve().parent
    for name, expected in EXAMPLES:
        path = examples_dir / name
        assembly = compile_file(path)
        vm = TernaryVM(compile_file_program(path)).run()
        print(name)
        print(f"  asm_lines: {len(assembly.splitlines())}")
        print(f"  output:    {_ints(vm.output)}")
        print(f"  match:     {_ints(vm.output) == expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
