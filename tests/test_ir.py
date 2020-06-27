try:
    from __kal_context__ import *
except:
    pass

import os

from typing import List, Optional

from kal_ir import LLVMCodeGenerator
from kal_ast import Node, CallExpr, Function, Prototype, BinaryExpr, NumberExpr, VariableExpr
from kal_eval import KaleidoscopeCodeEvaluator
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope/


def test_basic():
    e = KaleidoscopeCodeEvaluator()
    assert e.eval_expr("3") == 3
    assert e.eval_expr("3+3*4") == 15


def test_use_func():
    e = KaleidoscopeCodeEvaluator()
    assert e.eval_expr("def adder(x y) x+y") is None
    assert e.eval_expr("adder(5, 4) + adder(3, 2)") == 14


def test_use_libc():
    e = KaleidoscopeCodeEvaluator()
    assert e.eval_expr("extern ceil(x)") is None
    assert e.eval_expr("ceil(4.5)") == 5
    assert e.eval_expr("extern floor(x)") is None
    assert e.eval_expr("def cfadder(x) ceil(x) + floor(x)") is None
    assert e.eval_expr("cfadder(3.14)") == 7


def test_basic_if():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def foo(a b) a * if a < b then a + 1 else b + 1")
    assert e.eval_expr("foo(3, 4)") == 12
    assert e.eval_expr("foo(5, 4)") == 25


def test_nested_if():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr(
        """
        def foo(a b c)
            if a < b
                then if a < c then a * 2 else c * 2
                else b * 2"""
    )
    assert e.eval_expr("foo(1, 20, 300)") == 2
    assert e.eval_expr("foo(10, 2, 300)") == 4
    assert e.eval_expr("foo(100, 2000, 30)") == 60


def test_nested_if2():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr(
        """
        def min3(a b c)
            if a < b
                then if a < c
                    then a
                    else c
                else if b < c
                    then b
                    else c"""
    )
    assert e.eval_expr("min3(1, 2, 3)") == 1
    assert e.eval_expr("min3(1, 3, 2)") == 1
    assert e.eval_expr("min3(2, 1, 3)") == 1
    assert e.eval_expr("min3(2, 3, 1)") == 1
    assert e.eval_expr("min3(3, 1, 2)") == 1
    assert e.eval_expr("min3(3, 2, 1)") == 1
    assert e.eval_expr("min3(3, 3, 2)") == 2
    assert e.eval_expr("min3(3, 3, 3)") == 3


def test_for():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr(
        """
        def foo(a b c)
            if a < b
                then for x = 1, x < b, c in x+a+c*b
                else c * 2"""
    )
    assert e.eval_expr("foo(1, 2, 3)") == 0
    assert e.eval_expr("foo(3, 2, 30)") == 60


def test_custom_binop():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def binary% (a b) a - b")
    assert e.eval_expr("10 % 5") == 5
    assert e.eval_expr("100 % 5.5") == 94.5


def test_custom_unop():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def unary!(a) 0 - a")
    e.eval_expr("def unary^(a) a * a")
    assert e.eval_expr("!10") == -10
    assert e.eval_expr("^10") == 100
    assert e.eval_expr("!^10") == -100
    assert e.eval_expr("^!10") == 100


def test_mixed_ops():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def unary!(a) 0 - a")
    e.eval_expr("def unary^(a) a * a")
    e.eval_expr("def binary% (a b) a - b")
    assert e.eval_expr("!10 % !20") == 10
    assert e.eval_expr("^(!10 % !20)") == 100


def test_var_expr():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr(
        """
        def foo(x y z)
            var s1 = x + y, s2 = z + y in
                s1 * s2"""
    )
    assert e.eval_expr("foo(1, 2, 3)") == 15

    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def binary : 1 (x y) y")
    e.eval_expr(
        """
        def foo(step)
            var accum in
                (for i = 0, i < 10, step in
                    accum = accum + i) : accum"""
    )
    # NOTE Kaleidoscope's 'for' loop executes the last iteration even when the
    # condition is no longer fulfilled after the step is done: 0 + 2 + 4 + 6 + 8 + 10
    assert e.eval_expr("foo(2)") == 30


def test_nested_var_exprs():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr(
        """
        def foo(x y z)
            var s1 = x + y, s2 = z + y in
                var s3 = s1 * s2 in
                    s3 * 100
        """
    )
    assert e.eval_expr("foo(1, 2, 3)") == 1500


def test_assignments():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def binary : 1 (x y) y")
    e.eval_expr(
        """
        def foo(a b)
            var s, p, r in
                s = a + b :
                p = a * b :
                r = s + 100 * p :
                r
        """
    )
    assert e.eval_expr("foo(2, 3)") == 605
    assert e.eval_expr("foo(10, 20)") == 20030


def test_triple_assignment():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def binary : 1 (x y) y")
    e.eval_expr(
        """
        def foo(a)
            var x, y, z in
                x = y = z = a
                : x + 2 * y + 3 * z
        """
    )
    assert e.eval_expr("foo(5)") == 30


def test_compiling_to_object_code():
    e = KaleidoscopeCodeEvaluator()
    e.eval_expr("def average(x y) (x + y) * 0.5;")

    import llvmlite.binding as llvm

    obj = e.compile_to_object_code()
    obj_format = llvm.get_object_format()

    # Check the magic number of object format
    elf_magic = b"\x7fELF"
    macho_magic = b"\xfe\xed\xfa\xcf"
    if obj[:4] == elf_magic:
        assert obj_format == "ELF"
    elif obj[:4] == macho_magic:
        assert obj_format == "MachO"
    else:
        # There are too many variations of COFF magic number,
        # so we assume all other formats are COFF
        assert obj_format == "COFF"

    # NOTE uncoment to output the generated code
    # with open(os.path.join(os.path.dirname(__file__), "average.o"), "wb") as average_obj_file:
    #     average_obj_file.write(obj)
