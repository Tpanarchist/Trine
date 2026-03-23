"""Trine test suite — algebraic proofs and correctness verification."""

from pathlib import Path

import pytest
from trine import (
    Trit, coerce_trits, Tape,
    int_to_trits, trits_to_int, format_trits,
    TernaryMachine, ternary_abs, ternary_sub, ternary_cmp,
    ternary_min, ternary_max, ternary_cons, ternary_div, ternary_mod, ternary_mul,
    TernaryVM, Instruction, Op, VMError,
    AssemblerError, assemble, assemble_file,
    shift_left, shift_right, sign,
)
from trine.benchmarks import (
    benchmark_division_scaling,
    benchmark_operations,
    render_benchmark_report,
)


# ═══════════════════════════════════════════════════════════════
# Trit primitives
# ═══════════════════════════════════════════════════════════════

class TestTrit:
    def test_values(self):
        assert Trit.NEG == -1
        assert Trit.ZERO == 0
        assert Trit.POS == 1

    def test_coercion(self):
        assert Trit.coerce(-1) is Trit.NEG
        assert Trit.coerce(0) is Trit.ZERO
        assert Trit.coerce(1) is Trit.POS

    def test_invalid_coercion(self):
        with pytest.raises(ValueError, match="-1, 0, or"):
            Trit.coerce(2)

    def test_flip(self):
        assert Trit.NEG.flip() is Trit.POS
        assert Trit.POS.flip() is Trit.NEG
        assert Trit.ZERO.flip() is Trit.ZERO

    def test_labels_and_symbols(self):
        assert Trit.NEG.label == "NEG"
        assert Trit.ZERO.symbol == "0"
        assert Trit.POS.symbol == "+"


# ═══════════════════════════════════════════════════════════════
# Tape
# ═══════════════════════════════════════════════════════════════

class TestTape:
    def test_default_zero(self):
        tape = Tape()
        assert tape.read(0) is Trit.ZERO
        assert tape.read(-999) is Trit.ZERO

    def test_write_and_read(self):
        tape = Tape()
        tape.write(5, Trit.POS)
        assert tape.read(5) is Trit.POS

    def test_write_zero_deletes(self):
        tape = Tape()
        tape.write(3, Trit.NEG)
        tape.write(3, Trit.ZERO)
        assert 3 not in tape.as_dict()

    def test_sparse_storage(self):
        tape = Tape({-2: 1, 3: -1})
        assert tape.read(-2) is Trit.POS
        assert tape.read(3) is Trit.NEG
        assert len(tape) == 2


# ═══════════════════════════════════════════════════════════════
# Balanced ternary conversion
# ═══════════════════════════════════════════════════════════════

class TestFormatting:
    @pytest.mark.parametrize("value,expected", [
        (-4, "--"), (-1, "-"), (0, "0"), (1, "+"),
        (2, "+-"), (3, "+0"), (4, "++"), (5, "+--"), (13, "+++"),
    ])
    def test_round_trip(self, value, expected):
        trits = int_to_trits(value)
        assert trits_to_int(trits) == value
        assert format_trits(trits) == expected


# ═══════════════════════════════════════════════════════════════
# ALU operations
# ═══════════════════════════════════════════════════════════════

class TestIncrement:
    @pytest.mark.parametrize("value,expected", [
        (-5, -4), (-1, 0), (0, 1), (1, 2), (4, 5), (13, 14), (40, 41),
    ])
    def test_increment(self, value, expected):
        assert TernaryMachine("increment").load_int(value).run().to_int() == expected


class TestDecrement:
    @pytest.mark.parametrize("value,expected", [
        (5, 4), (1, 0), (0, -1), (-1, -2), (-4, -5), (14, 13), (41, 40),
    ])
    def test_decrement(self, value, expected):
        assert TernaryMachine("decrement").load_int(value).run().to_int() == expected


class TestNegate:
    @pytest.mark.parametrize("value,expected", [
        (1, -1), (-1, 1), (5, -5), (-13, 13), (0, 0), (40, -40),
    ])
    def test_negate(self, value, expected):
        assert TernaryMachine("negate").load_int(value).run().to_int() == expected


class TestAddition:
    @pytest.mark.parametrize("a,b,expected", [
        (0, 0, 0), (1, 1, 2), (1, -1, 0), (13, 14, 27),
        (-13, 13, 0), (40, -40, 0), (5, 7, 12), (-5, -7, -12),
        (40, 41, 81), (100, 200, 300), (-100, -200, -300),
    ])
    def test_addition(self, a, b, expected):
        assert TernaryMachine("add").load_two(a, b).run().to_int() == expected


class TestMachineReuse:
    def test_add_machine_reuse_clears_second_tape_for_load_int(self):
        machine = TernaryMachine("add")
        assert machine.load_two(1, 2).run().to_int() == 3
        assert machine.load_int(5).run().to_int() == 5

    def test_add_machine_reuse_clears_second_tape_for_load_trits(self):
        machine = TernaryMachine("add")
        assert machine.load_two(1, 2).run().to_int() == 3
        assert machine.load_trits(int_to_trits(5)).run().to_int() == 5


class TestComposite:
    @pytest.mark.parametrize("value,expected", [
        (-1, 1), (-5, 5), (-13, 13), (-40, 40), (0, 0), (13, 13),
    ])
    def test_abs(self, value, expected):
        assert ternary_abs(value) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (5, 3, 2), (0, 1, -1), (13, 14, -1), (100, 42, 58),
    ])
    def test_sub(self, a, b, expected):
        assert ternary_sub(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (0, 5, 0), (1, 1, 1), (2, 3, 6), (13, 14, 182), (-5, 7, -35),
    ])
    def test_mul(self, a, b, expected):
        assert ternary_mul(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, -1), (5, 5, 0), (13, -4, 1), (-7, -2, -1),
    ])
    def test_cmp(self, a, b, expected):
        assert ternary_cmp(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 1), (5, 5, 5), (13, -4, -4), (-7, -2, -7),
    ])
    def test_min(self, a, b, expected):
        assert ternary_min(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 2), (5, 5, 5), (13, -4, 13), (-7, -2, -2),
    ])
    def test_max(self, a, b, expected):
        assert ternary_max(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (1, 1, 1), (0, 0, 0), (-4, -4, -4), (1, -1, 0), (5, 0, 0),
    ])
    def test_cons(self, a, b, expected):
        assert ternary_cons(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (7, 3, 2), (-7, 3, -2), (7, -3, -2), (-7, -3, 2), (2, 5, 0),
    ])
    def test_div(self, a, b, expected):
        assert ternary_div(a, b) == expected

    @pytest.mark.parametrize("a,b,expected", [
        (7, 3, 1), (-7, 3, -1), (7, -3, 1), (-7, -3, -1), (2, 5, 2),
    ])
    def test_mod(self, a, b, expected):
        assert ternary_mod(a, b) == expected

    def test_div_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError, match="division by zero"):
            ternary_div(7, 0)

    def test_mod_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError, match="division by zero"):
            ternary_mod(7, 0)

    @pytest.mark.parametrize("value,expected", [
        (0, 0), (1, 3), (-1, -3), (13, 39),
    ])
    def test_shift_left(self, value, expected):
        assert shift_left(value) == expected

    @pytest.mark.parametrize("value,expected", [
        (0, 0), (3, 1), (-3, -1), (5, 1), (13, 4), (40, 13), (-40, -13),
    ])
    def test_shift_right(self, value, expected):
        assert shift_right(value) == expected

    @pytest.mark.parametrize("value,expected", [
        (10**30 + 2, (10**30 + 2) // 3),
        (-(10**30 + 2), -((10**30 + 2) // 3)),
    ])
    def test_shift_right_large_exact(self, value, expected):
        assert shift_right(value) == expected


# ═══════════════════════════════════════════════════════════════
# Algebraic proofs
# ═══════════════════════════════════════════════════════════════

PROOF_VALUES = [-40, -13, -5, -1, 0, 1, 5, 13, 40]


class TestAlgebraicProofs:
    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_symmetry_inc_dec(self, n):
        """inc(dec(n)) == n == dec(inc(n))"""
        a = TernaryMachine("increment").load_int(
            TernaryMachine("decrement").load_int(n).run().to_int()
        ).run().to_int()
        b = TernaryMachine("decrement").load_int(
            TernaryMachine("increment").load_int(n).run().to_int()
        ).run().to_int()
        assert a == n == b

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_involution_negate(self, n):
        """neg(neg(n)) == n"""
        nn = TernaryMachine("negate").load_int(
            TernaryMachine("negate").load_int(n).run().to_int()
        ).run().to_int()
        assert nn == n

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_additive_identity(self, n):
        """n + 0 == n"""
        assert TernaryMachine("add").load_two(n, 0).run().to_int() == n

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_additive_inverse(self, n):
        """n + (-n) == 0"""
        neg_n = TernaryMachine("negate").load_int(n).run().to_int()
        assert TernaryMachine("add").load_two(n, neg_n).run().to_int() == 0

    @pytest.mark.parametrize("a,b", [(1, 2), (13, -5), (-40, 27), (0, 13)])
    def test_commutativity(self, a, b):
        """a + b == b + a"""
        ab = TernaryMachine("add").load_two(a, b).run().to_int()
        ba = TernaryMachine("add").load_two(b, a).run().to_int()
        assert ab == ba

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_inc_equals_add_one(self, n):
        """inc(n) == n + 1"""
        inc = TernaryMachine("increment").load_int(n).run().to_int()
        add = TernaryMachine("add").load_two(n, 1).run().to_int()
        assert inc == add

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_dec_equals_add_neg_one(self, n):
        """dec(n) == n + (-1)"""
        dec = TernaryMachine("decrement").load_int(n).run().to_int()
        add = TernaryMachine("add").load_two(n, -1).run().to_int()
        assert dec == add

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_shift_inverse(self, n):
        """shr(shl(n)) == n"""
        assert shift_right(shift_left(n)) == n

    @pytest.mark.parametrize("a,b", [(1, 2), (13, -5), (-40, 27)])
    def test_distributivity_negate_over_add(self, a, b):
        """neg(a+b) == neg(a) + neg(b)"""
        lhs = TernaryMachine("negate").load_int(
            TernaryMachine("add").load_two(a, b).run().to_int()
        ).run().to_int()
        rhs = TernaryMachine("add").load_two(
            TernaryMachine("negate").load_int(a).run().to_int(),
            TernaryMachine("negate").load_int(b).run().to_int(),
        ).run().to_int()
        assert lhs == rhs

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_abs_idempotent(self, n):
        """abs(abs(n)) == abs(n)"""
        assert ternary_abs(ternary_abs(n)) == ternary_abs(n)

    @pytest.mark.parametrize("a,b", [(1, 2), (13, -5), (-40, 27), (0, 13)])
    def test_min_commutative(self, a, b):
        assert ternary_min(a, b) == ternary_min(b, a)

    @pytest.mark.parametrize("a,b", [(1, 2), (13, -5), (-40, 27), (0, 13)])
    def test_max_commutative(self, a, b):
        assert ternary_max(a, b) == ternary_max(b, a)

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_min_idempotent(self, n):
        assert ternary_min(n, n) == n

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_max_idempotent(self, n):
        assert ternary_max(n, n) == n

    @pytest.mark.parametrize("n", PROOF_VALUES)
    def test_cons_identity(self, n):
        assert ternary_cons(n, n) == n

    @pytest.mark.parametrize("a,b", [(1, 2), (13, -5), (-40, 27), (0, 13)])
    def test_cons_disagreement_returns_zero(self, a, b):
        assert ternary_cons(a, b) == 0

    @pytest.mark.parametrize("a,b", [(7, 3), (-7, 3), (7, -3), (-7, -3), (2, 5)])
    def test_div_mod_recombine(self, a, b):
        q = ternary_div(a, b)
        r = ternary_mod(a, b)
        assert a == q * b + r
        assert abs(r) < abs(b)


# ═══════════════════════════════════════════════════════════════
# VM programs
# ═══════════════════════════════════════════════════════════════

class TestVM:
    def test_simple_arithmetic(self):
        """(13 + 14) * 3 = 81"""
        prog = [
            Instruction(Op.PUSH, 13), Instruction(Op.PUSH, 14),
            Instruction(Op.ADD), Instruction(Op.SHL),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert vm.output[0].startswith("81")

    def test_three_way_branch(self):
        """BR3 dispatches correctly on sign."""
        for val, expected in [(-7, -1), (0, 0), (42, 1)]:
            prog = [
                Instruction(Op.PUSH, val), Instruction(Op.SGN),
                Instruction(Op.BR3, (3, 5, 7)),
                Instruction(Op.PUSH, -1), Instruction(Op.JMP, 8),
                Instruction(Op.PUSH, 0), Instruction(Op.JMP, 8),
                Instruction(Op.PUSH, 1),
                Instruction(Op.PRINT), Instruction(Op.HALT),
            ]
            vm = TernaryVM(prog).run()
            assert int(vm.output[0].split()[0]) == expected

    def test_counting_loop(self):
        """Count 1 to 5."""
        prog = [
            Instruction(Op.PUSH, 0),
            Instruction(Op.INC),
            Instruction(Op.DUP), Instruction(Op.PRINT),
            Instruction(Op.DUP), Instruction(Op.PUSH, 5), Instruction(Op.SUB),
            Instruction(Op.JZ, 9), Instruction(Op.JMP, 1),
            Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        actual = [int(o.split()[0]) for o in vm.output]
        assert actual == [1, 2, 3, 4, 5]

    def test_factorial_unrolled(self):
        """5! = 120"""
        prog = [
            Instruction(Op.PUSH, 1),
            Instruction(Op.PUSH, 2), Instruction(Op.MUL),
            Instruction(Op.PUSH, 3), Instruction(Op.MUL),
            Instruction(Op.PUSH, 4), Instruction(Op.MUL),
            Instruction(Op.PUSH, 5), Instruction(Op.MUL),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 120

    def test_factorial_loop(self):
        """6! = 720 via loop with OVER."""
        prog = [
            Instruction(Op.PUSH, 6), Instruction(Op.PUSH, 1),
            Instruction(Op.OVER), Instruction(Op.JP, 5), Instruction(Op.JMP, 11),
            Instruction(Op.OVER), Instruction(Op.MUL),
            Instruction(Op.SWAP), Instruction(Op.DEC), Instruction(Op.SWAP),
            Instruction(Op.JMP, 2),
            Instruction(Op.SWAP), Instruction(Op.POP),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 720

    def test_fibonacci(self):
        """First 8 Fibonacci numbers."""
        prog = [
            Instruction(Op.PUSH, 0), Instruction(Op.DUP), Instruction(Op.PRINT),
            Instruction(Op.PUSH, 1),
        ]
        for _ in range(7):
            prog.extend([
                Instruction(Op.DUP), Instruction(Op.PRINT), Instruction(Op.SWAP),
                Instruction(Op.OVER), Instruction(Op.ADD),
            ])
        prog.append(Instruction(Op.HALT))
        vm = TernaryVM(prog).run()
        actual = [int(o.split()[0]) for o in vm.output]
        assert actual == [0, 1, 1, 2, 3, 5, 8, 13]

    def test_doubling_via_add(self):
        """Doubling via self-addition: n+n == 2n."""
        prog = [
            Instruction(Op.PUSH, 21),
            Instruction(Op.DUP), Instruction(Op.ADD),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 42

    def test_rot_rotates_top_three(self):
        prog = [
            Instruction(Op.PUSH, 1),
            Instruction(Op.PUSH, 2),
            Instruction(Op.PUSH, 3),
            Instruction(Op.ROT),
            Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert vm.stack == [2, 3, 1]

    def test_memory_load_default_zero(self):
        prog = [
            Instruction(Op.PUSH, 7),
            Instruction(Op.LOAD), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 0
        assert vm.memory == {}

    def test_memory_store_and_load_round_trip(self):
        prog = [
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 13), Instruction(Op.STORE),
            Instruction(Op.PUSH, 4), Instruction(Op.LOAD),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 13
        assert vm.memory == {4: 13}

    def test_memory_store_zero_deletes_cell(self):
        prog = [
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 13), Instruction(Op.STORE),
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 0), Instruction(Op.STORE),
            Instruction(Op.PUSH, 4), Instruction(Op.LOAD),
            Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 0
        assert vm.memory == {}

    def test_compare_returns_balanced_trit(self):
        for a, b, expected in [(1, 2, -1), (5, 5, 0), (13, -4, 1)]:
            prog = [
                Instruction(Op.PUSH, a), Instruction(Op.PUSH, b),
                Instruction(Op.CMP), Instruction(Op.PRINT), Instruction(Op.HALT),
            ]
            vm = TernaryVM(prog).run()
            assert int(vm.output[0].split()[0]) == expected

    def test_min_returns_lesser_value(self):
        prog = [
            Instruction(Op.PUSH, 13), Instruction(Op.PUSH, -4),
            Instruction(Op.MIN), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -4

    def test_max_returns_greater_value(self):
        prog = [
            Instruction(Op.PUSH, 13), Instruction(Op.PUSH, -4),
            Instruction(Op.MAX), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 13

    def test_cons_returns_equal_value_or_zero(self):
        prog_equal = [
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 4),
            Instruction(Op.CONS), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        prog_unequal = [
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, -4),
            Instruction(Op.CONS), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm_equal = TernaryVM(prog_equal).run()
        vm_unequal = TernaryVM(prog_unequal).run()
        assert int(vm_equal.output[0].split()[0]) == 4
        assert int(vm_unequal.output[0].split()[0]) == 0

    def test_div_uses_truncation_toward_zero(self):
        prog = [
            Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
            Instruction(Op.DIV), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -2

    def test_mod_matches_dividend_sign(self):
        prog = [
            Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
            Instruction(Op.MOD), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -1

    def test_div_by_zero_raises_vm_error(self):
        prog = [
            Instruction(Op.PUSH, 7), Instruction(Op.PUSH, 0),
            Instruction(Op.DIV), Instruction(Op.HALT),
        ]
        with pytest.raises(VMError, match="division by zero"):
            TernaryVM(prog).run()

    def test_mod_by_zero_raises_vm_error(self):
        prog = [
            Instruction(Op.PUSH, 7), Instruction(Op.PUSH, 0),
            Instruction(Op.MOD), Instruction(Op.HALT),
        ]
        with pytest.raises(VMError, match="division by zero"):
            TernaryVM(prog).run()

    def test_mul_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 2), Instruction(Op.PUSH, 3),
            Instruction(Op.MUL), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 6
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_cmp_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 2), Instruction(Op.PUSH, 3),
            Instruction(Op.CMP), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -1
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_min_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 13), Instruction(Op.PUSH, -4),
            Instruction(Op.MIN), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -4
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_max_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 13), Instruction(Op.PUSH, -4),
            Instruction(Op.MAX), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 13
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_cons_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 4), Instruction(Op.PUSH, 4),
            Instruction(Op.CONS), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 4
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_div_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
            Instruction(Op.DIV), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -2
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_mod_tracks_composite_ops_and_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, -7), Instruction(Op.PUSH, 3),
            Instruction(Op.MOD), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == -1
        assert vm.composite_ops == 1
        assert vm.alu_ticks > 0

    def test_shift_tracks_composite_ops_without_primitive_ticks(self):
        prog = [
            Instruction(Op.PUSH, 13),
            Instruction(Op.SHL), Instruction(Op.PRINT), Instruction(Op.HALT),
        ]
        vm = TernaryVM(prog).run()
        assert int(vm.output[0].split()[0]) == 39
        assert vm.composite_ops == 1
        assert vm.alu_ticks == 0


class TestAssembler:
    def test_assemble_simple_program(self):
        program = assemble(
            """
            ; comment
            PUSH 4
            PUSH 13
            STORE
            PUSH 4
            LOAD
            PRINT
            HALT
            """
        )
        assert program == [
            Instruction(Op.PUSH, 4),
            Instruction(Op.PUSH, 13),
            Instruction(Op.STORE),
            Instruction(Op.PUSH, 4),
            Instruction(Op.LOAD),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]

    def test_assemble_br3_targets(self):
        program = assemble(
            """
            PUSH -7
            SGN
            BR3 3, 5, 7
            HALT
            """
        )
        assert program[2] == Instruction(Op.BR3, (3, 5, 7))

    def test_assemble_rot(self):
        program = assemble(
            """
            PUSH 1
            PUSH 2
            PUSH 3
            ROT
            HALT
            """
        )
        assert program[3] == Instruction(Op.ROT)

    def test_assemble_min_max_cons(self):
        program = assemble(
            """
            PUSH 13
            PUSH -4
            MIN
            PUSH 13
            PUSH -4
            MAX
            PUSH 4
            PUSH 4
            CONS
            HALT
            """
        )
        assert program[2] == Instruction(Op.MIN)
        assert program[5] == Instruction(Op.MAX)
        assert program[8] == Instruction(Op.CONS)

    def test_assemble_div_mod(self):
        program = assemble(
            """
            PUSH -7
            PUSH 3
            DIV
            PUSH -7
            PUSH 3
            MOD
            HALT
            """
        )
        assert program[2] == Instruction(Op.DIV)
        assert program[5] == Instruction(Op.MOD)

    def test_assemble_resolves_jump_label(self):
        program = assemble(
            """
            JMP done
            PUSH 99
            done: HALT
            """
        )
        assert program[0] == Instruction(Op.JMP, 2)

    def test_assemble_resolves_br3_labels(self):
        program = assemble(
            """
            PUSH -7
            SGN
            BR3 neg_case, zero_case, pos_case
            neg_case: PUSH -1
            JMP done
            zero_case: PUSH 0
            JMP done
            pos_case: PUSH 1
            done: PRINT
            HALT
            """
        )
        assert program[2] == Instruction(Op.BR3, (3, 5, 7))

    def test_assemble_rejects_unknown_opcode(self):
        with pytest.raises(AssemblerError, match="unknown opcode"):
            assemble("NOPE")

    def test_assemble_rejects_missing_operand(self):
        with pytest.raises(AssemblerError, match="requires an integer operand"):
            assemble("PUSH")

    def test_assemble_rejects_extra_operand(self):
        with pytest.raises(AssemblerError, match="takes no operand"):
            assemble("HALT 1")

    def test_assemble_rejects_invalid_br3_operand(self):
        with pytest.raises(AssemblerError, match="three comma-separated targets"):
            assemble("BR3 1, 2")

    def test_assemble_rejects_duplicate_label(self):
        with pytest.raises(AssemblerError, match="duplicate label"):
            assemble(
                """
                loop: PUSH 1
                loop: HALT
                """
            )

    def test_assemble_rejects_unknown_target_label(self):
        with pytest.raises(AssemblerError, match="requires a valid target"):
            assemble("JMP missing_label")

    def test_assembled_program_executes(self):
        program = assemble(
            """
            PUSH 1
            PUSH 2
            MUL
            PUSH 3
            MUL
            PUSH 4
            MUL
            PUSH 5
            MUL
            PRINT
            HALT
            """
        )
        vm = TernaryVM(program).run()
        assert int(vm.output[0].split()[0]) == 120

    def test_labeled_program_executes(self):
        program = assemble(
            """
            PUSH 0
            loop:
            INC
            DUP
            PRINT
            DUP
            PUSH 5
            SUB
            JZ done
            JMP loop
            done:
            HALT
            """
        )
        vm = TernaryVM(program).run()
        assert [int(o.split()[0]) for o in vm.output] == [1, 2, 3, 4, 5]

    def test_rot_program_executes(self):
        program = assemble(
            """
            PUSH 1
            PUSH 2
            PUSH 3
            ROT
            HALT
            """
        )
        vm = TernaryVM(program).run()
        assert vm.stack == [2, 3, 1]

    def test_min_max_cons_program_executes(self):
        program = assemble(
            """
            PUSH 13
            PUSH -4
            MIN
            PRINT
            PUSH 13
            PUSH -4
            MAX
            PRINT
            PUSH 4
            PUSH 4
            CONS
            PRINT
            PUSH 4
            PUSH -4
            CONS
            PRINT
            HALT
            """
        )
        vm = TernaryVM(program).run()
        assert [int(o.split()[0]) for o in vm.output] == [-4, 13, 4, 0]

    def test_div_mod_program_executes(self):
        program = assemble(
            """
            PUSH -7
            PUSH 3
            DIV
            PRINT
            PUSH -7
            PUSH 3
            MOD
            PRINT
            HALT
            """
        )
        vm = TernaryVM(program).run()
        assert [int(o.split()[0]) for o in vm.output] == [-2, -1]

    def test_assemble_file_example(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "factorial.trine"
        program = assemble_file(path)
        vm = TernaryVM(program).run()
        assert int(vm.output[0].split()[0]) == 120


class TestBenchmarks:
    def test_operation_benchmarks_cover_div_mod(self):
        labels = {row.name for row in benchmark_operations()}
        assert {"DIV -7 3", "MOD -7 3"} <= labels

    def test_division_scaling_benchmarks_increase_with_quotient(self):
        rows = benchmark_division_scaling(dividends=(3, 9, 27), divisor=3)
        assert [row.quotient for row in rows] == [1, 3, 9]
        assert rows[0].alu_ticks < rows[1].alu_ticks < rows[2].alu_ticks

    def test_render_benchmark_report_mentions_division_growth(self):
        report = render_benchmark_report()
        assert "Operation Snapshot" in report
        assert "Program Snapshot" in report
        assert "DIV 81 3" in report
