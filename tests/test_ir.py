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
    assert e.evaluate("3") == 3
    assert e.evaluate("3+3*4") == 15


def test_use_func():
    e = KaleidoscopeCodeEvaluator()
    assert e.evaluate("def adder(x y) x+y") is None
    assert e.evaluate("adder(5, 4) + adder(3, 2)") == 14


def test_use_libc():
    e = KaleidoscopeCodeEvaluator()
    assert e.evaluate("extern ceil(x)") is None
    assert e.evaluate("ceil(4.5)") == 5
    assert e.evaluate("extern floor(x)") is None
    assert e.evaluate("def cfadder(x) ceil(x) + floor(x)") is None
    assert e.evaluate("cfadder(3.14)") == 7


def test_basic_if():
    e = KaleidoscopeCodeEvaluator()
    e.evaluate("def foo(a b) a * if a < b then a + 1 else b + 1")
    assert e.evaluate("foo(3, 4)") == 12
    assert e.evaluate("foo(5, 4)") == 25


def test_nested_if():
    e = KaleidoscopeCodeEvaluator()
    e.evaluate(
        """
        def foo(a b c)
            if a < b
                then if a < c then a * 2 else c * 2
                else b * 2"""
    )
    assert e.evaluate("foo(1, 20, 300)") == 2
    assert e.evaluate("foo(10, 2, 300)") == 4
    assert e.evaluate("foo(100, 2000, 30)") == 60


def test_for():
    e = KaleidoscopeCodeEvaluator()
    e.evaluate(
        """
        def foo(a b c)
            if a < b
                then for x = 1, x < b, c in x+a+c*b
                else c * 2"""
    )
    assert e.evaluate("foo(1, 2, 3)") == 0
    assert e.evaluate("foo(3, 2, 30)") == 60
