# Trine Benchmark Note

Generated from `python -m trine.benchmarks`.

These are deterministic machine-model metrics from the current Python
reference implementation. They are not wall-clock benchmarks and should
not be used to make runtime or hardware-efficiency claims.

## Operation Snapshot

| Case | Result | VM Steps | ALU Ticks | Composite Ops |
| --- | --- | --- | --- | --- |
| INC 13 | 14 | 4 | 4 | 0 |
| DEC 13 | 12 | 4 | 1 | 0 |
| NEG -13 | 13 | 4 | 3 | 0 |
| ADD 13 14 | 27 | 5 | 4 | 0 |
| ABS -13 | 13 | 4 | 3 | 1 |
| SUB 13 14 | -1 | 5 | 8 | 1 |
| CMP 13 14 | -1 | 5 | 8 | 1 |
| MIN 13 -4 | -4 | 5 | 6 | 1 |
| MAX 13 -4 | 13 | 5 | 6 | 1 |
| CONS 4 4 | 4 | 5 | 4 | 1 |
| DIV -7 3 | -2 | 5 | 31 | 1 |
| MOD -7 3 | -1 | 5 | 31 | 1 |
| MUL 13 -4 | -52 | 5 | 15 | 1 |
| SHL 13 | 39 | 4 | 0 | 1 |
| SHR 13 | 4 | 4 | 0 | 1 |
| SGN -13 | -1 | 4 | 0 | 1 |

## Program Snapshot

| Case | Result | VM Steps | ALU Ticks | Composite Ops |
| --- | --- | --- | --- | --- |
| call_ret_round_trip | - | 3 | 0 | 2 |
| call_leaf | 9 | 80 | 37 | 8 |
| factorial_call_recursive | 120 | 414 | 226 | 51 |
| factorial_unrolled | 120 | 11 | 38 | 4 |
| factorial_loop | 720 | 57 | 76 | 6 |
| count_to_five_asm | 1, 2, 3, 4, 5 | 41 | 38 | 5 |
| memory_round_trip | 13 | 7 | 0 | 0 |
| fibonacci_8 | 0, 1, 1, 2, 3, 5, 8, 13 | 40 | 18 | 0 |
| powers_of_two_8 | 1, 2, 4, 8, 16, 32, 64, 128 | 32 | 26 | 0 |

`CALL` and `RET` are composite control-flow instructions. They affect
`composite_ops` but do not contribute to `alu_ticks` directly.

## Division Cost Growth

| Case | Quotient | VM Steps | ALU Ticks | Composite Ops |
| --- | --- | --- | --- | --- |
| DIV 3 3 | 1 | 5 | 13 | 1 |
| DIV 9 3 | 3 | 5 | 36 | 1 |
| DIV 27 3 | 9 | 5 | 115 | 1 |
| DIV 81 3 | 27 | 5 | 386 | 1 |

`DIV` and `MOD` currently use repeated subtraction over absolute values, plus
sign-fixup. In this reference model, their ALU tick cost therefore grows
roughly linearly with quotient magnitude.
