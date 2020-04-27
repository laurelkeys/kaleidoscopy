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
    assert e.evaluate("3") == 3.0
    assert e.evaluate("3+3*4") == 15.0


def test_use_func():
    e = KaleidoscopeCodeEvaluator()
    assert e.evaluate("def adder(x y) x+y") is None
    assert e.evaluate("adder(5, 4) + adder(3, 2)") == 14.0


def test_use_libc():
    e = KaleidoscopeCodeEvaluator()
    assert e.evaluate("extern ceil(x)") is None
    assert e.evaluate("ceil(4.5)") == 5.0
    assert e.evaluate("extern floor(x)") is None
    assert e.evaluate("def cfadder(x) ceil(x) + floor(x)") is None
    assert e.evaluate("cfadder(3.14)") == 7.0


if __name__ == "__main__":
    e = KaleidoscopeCodeEvaluator()
    print(e.evaluate("def adder(a b) a + b"))
    print(e.evaluate("def foo(x) (1+2+x)*(x+(1+2))"))
    print(e.evaluate("foo(3)"))
    print(e.evaluate("foo(adder(3, 3)*4)", optimize=True, llvmdump=True))
