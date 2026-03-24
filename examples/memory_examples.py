"""Run the memory-heavy Trine assembly examples in list and image modes."""

from __future__ import annotations

from pathlib import Path

from trine import TernaryVM, assemble_file, assemble_file_image


EXAMPLES = [
    "array_sum.trine",
    "linked_list_walk.trine",
    "state_table_fsm.trine",
]


def _run(path: Path) -> tuple[list[str], list[str]]:
    vm_list = TernaryVM(assemble_file(path)).run()
    vm_image = TernaryVM(assemble_file_image(path)).run()
    return vm_list.output, vm_image.output


def main() -> int:
    examples_dir = Path(__file__).resolve().parent
    for name in EXAMPLES:
        path = examples_dir / name
        list_output, image_output = _run(path)
        print(f"\n{name}")
        print(f"  list : {list_output}")
        print(f"  image: {image_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
