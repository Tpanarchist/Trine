from pathlib import Path

from trine import TernaryVM, assemble_file, assemble_file_image


EXAMPLES = [
    ("call_leaf.trine", [9]),
    ("factorial_call.trine", [120]),
]


def _ints(output: list[str]) -> list[int]:
    return [int(item.split()[0]) for item in output]


def main() -> int:
    examples_dir = Path(__file__).resolve().parent
    for name, expected in EXAMPLES:
        path = examples_dir / name
        vm_list = TernaryVM(assemble_file(path)).run()
        vm_image = TernaryVM(assemble_file_image(path)).run()
        print(name)
        print(f"  list:  {_ints(vm_list.output)}")
        print(f"  image: {_ints(vm_image.output)}")
        print(f"  match: {_ints(vm_list.output) == _ints(vm_image.output) == expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
