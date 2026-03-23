"""Trine test suite — algebraic proofs and correctness verification."""

import pytest
from trine import (
    Trit, coerce_trits, Tape,
    int_to_trits, trits_to_int, format_trits,
    TernaryMachine, ternary_abs, ternary_sub, ternary_mul,
    TernaryVM, Instruction, Op,
    shift_left, shift_right, sign,
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
