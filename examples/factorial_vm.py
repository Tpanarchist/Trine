"""Minimal VM example: factorial(5)."""

from trine import Instruction, Op, TernaryVM


def main() -> int:
    program = [
        Instruction(Op.PUSH, 1),
        Instruction(Op.PUSH, 2), Instruction(Op.MUL),
        Instruction(Op.PUSH, 3), Instruction(Op.MUL),
        Instruction(Op.PUSH, 4), Instruction(Op.MUL),
        Instruction(Op.PUSH, 5), Instruction(Op.MUL),
        Instruction(Op.PRINT), Instruction(Op.HALT),
    ]
    vm = TernaryVM(program).run()
    for line in vm.output:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
