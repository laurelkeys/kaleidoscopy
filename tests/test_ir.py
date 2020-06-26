try:
    from context import *
except:
    pass

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
