"""Assemble and run the factorial assembly example."""

from __future__ import annotations

from pathlib import Path

from trine import TernaryVM, assemble_file


def main() -> int:
    program_path = Path(__file__).with_name("factorial.trine")
    program = assemble_file(program_path)
    vm = TernaryVM(program).run()
    for line in vm.output:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
