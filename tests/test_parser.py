try:
    from context import *
except:
    pass

from typing import List, Optional

from kal_ast import Node, CallExpr, Function, Prototype, BinaryExpr, NumberExpr, VariableExpr
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope/


def _flatten(ast: Node):
    if isinstance(ast, NumberExpr):
        return ["Number", ast.val]
    elif isinstance(ast, VariableExpr):
        return ["Variable", ast.name]
    elif isinstance(ast, BinaryExpr):
        return ["Binop", ast.op, _flatten(ast.lhs), _flatten(ast.rhs)]
    elif isinstance(ast, CallExpr):
        args = [_flatten(arg) for arg in ast.args]
        return ["Call", ast.callee, args]
    elif isinstance(ast, Prototype):
        return ["Proto", ast.name, " ".join(ast.params)]
    elif isinstance(ast, Function):
        return ["Function", _flatten(ast.proto), _flatten(ast.body)]
    else:
        raise TypeError(f"Unknown type '{type(ast)}' in _flatten")


def _assert_body(top_level: Optional[Node], expected: List[str]):
    assert isinstance(top_level, Function)
    assert all([a == b for a, b in zip(_flatten(top_level.body), expected)])


def test_basic():
    ast = next(Parser().parse("2"))
    assert isinstance(ast, Function)
    assert isinstance(ast.body, NumberExpr)
    assert ast.body.val == "2"


def test_basic_with_flattening():
    ast = next(Parser().parse("2"))
    _assert_body(ast, ["Number", "2"])

    ast = next(Parser().parse("foobar"))
    _assert_body(ast, ["Variable", "foobar"])


def test_expr_singleprec():
    ast = next(Parser().parse("2+ 3-4"))
    _assert_body(
        ast, ["Binop", "-", ["Binop", "+", ["Number", "2"], ["Number", "3"]], ["Number", "4"],],
    )


def test_expr_multiprec():
    ast = next(Parser().parse("2+3*4-9"))
    _assert_body(
        ast,
        [
            "Binop",
            "-",
            ["Binop", "+", ["Number", "2"], ["Binop", "*", ["Number", "3"], ["Number", "4"]],],
            ["Number", "9"],
        ],
    )


def test_expr_parens():
    ast = next(Parser().parse("2*(3-4)*7"))
    _assert_body(
        ast,
        [
            "Binop",
            "*",
            ["Binop", "*", ["Number", "2"], ["Binop", "-", ["Number", "3"], ["Number", "4"]],],
            ["Number", "7"],
        ],
    )


def test_externals():
    ast = next(Parser().parse("extern sin(arg)"))
    assert all([a == b for a, b in zip(_flatten(ast), ["Proto", "sin", "arg"])])

    ast = next(Parser().parse("extern Foobar(nom denom abom)"))
    assert all([a == b for a, b in zip(_flatten(ast), ["Proto", "Foobar", "nom denom abom"])])


def test_funcdef():
    ast = next(Parser().parse("def foo(x) 1 + bar(x)"))
    assert all(
        [
            a == b
            for a, b in zip(
                _flatten(ast),
                [
                    "Function",
                    ["Proto", "foo", "x"],
                    ["Binop", "+", ["Number", "1"], ["Call", "bar", [["Variable", "x"]]],],
                ],
            )
        ]
    )
