try:
    from context import *
except:
    pass

from typing import List, Optional

from kal_ast import (
    Node,
    CallExpr,
    Function,
    Prototype,
    UnaryExpr,
    VarInExpr,
    BinaryExpr,
    NumberExpr,
    VariableExpr,
)
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope/


def _flatten(ast: Node):
    if isinstance(ast, NumberExpr):
        return ["Number", ast.val]
    elif isinstance(ast, VariableExpr):
        return ["Variable", ast.name]
    elif isinstance(ast, BinaryExpr):
        return ["Binop", ast.op, _flatten(ast.lhs), _flatten(ast.rhs)]
    elif isinstance(ast, UnaryExpr):
        return ["Unary", ast.op, _flatten(ast.operand)]
    elif isinstance(ast, CallExpr):
        args = [_flatten(arg) for arg in ast.args]
        return ["Call", ast.callee, args]
    elif isinstance(ast, Prototype):
        return ["Proto", ast.name, " ".join(ast.params)]
    elif isinstance(ast, Function):
        return ["Function", _flatten(ast.proto), _flatten(ast.body)]
    elif isinstance(ast, VarInExpr):
        return [
            "VarIn",
            [[name, _flatten(init) if init else None] for (name, init) in ast.var_names],
            _flatten(ast.body_expr),
        ]
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


def test_unary():
    p = Parser()
    ast = next(p.parse("def unary!(x) 0 - x"))
    assert isinstance(ast, Function)
    proto = ast.proto
    assert isinstance(proto, Prototype)
    assert proto.is_operator
    assert proto.name == "unary!"

    ast = next(p.parse("!a + !b - !!c"))
    _assert_body(
        ast,
        [
            "Binop",
            "-",
            ["Binop", "+", ["Unary", "!", ["Variable", "a"]], ["Unary", "!", ["Variable", "b"]]],
            ["Unary", "!", ["Unary", "!", ["Variable", "c"]]],
        ],
    )


def test_binary_op_with_prec():
    ast = next(Parser().parse("def binary% 77(a b) a + b"))
    assert isinstance(ast, Function)
    proto = ast.proto
    assert isinstance(proto, Prototype)
    assert proto.is_operator
    assert proto.bin_op_precedence == 77
    assert proto.name == "binary%"


def test_binop_relative_precedence():
    # with precedence 77, % binds stronger than all existing ops
    p = Parser()
    p.parse("def binary% 77(a b) a + b")
    ast = next(p.parse("a * 10 % 5 * 10"))
    _assert_body(
        ast,
        [
            "Binop",
            "*",
            ["Binop", "*", ["Variable", "a"], ["Binop", "%", ["Number", "10"], ["Number", "5"]]],
            ["Number", "10"],
        ],
    )

    ast = next(p.parse("a % 20 * 5"))
    _assert_body(
        ast, ["Binop", "*", ["Binop", "%", ["Variable", "a"], ["Number", "20"]], ["Number", "5"]]
    )


def test_binary_op_no_prec():
    ast = next(Parser().parse("def binary $(a b) a + b"))
    assert isinstance(ast, Function)
    proto = ast.proto
    assert isinstance(proto, Prototype)
    assert proto.is_operator
    assert proto.bin_op_precedence == 30
    assert proto.name == "binary$"


def test_assignment():
    p = Parser()
    ast = next(p.parse("def text(x) x = 5"))
    _assert_body(ast, ["Binop", "=", ["Variable", "x"], ["Number", "5"]])


def test_varexpr():
    p = Parser()
    ast = next(p.parse("def foo(x y) var t = 1 in y"))
    _assert_body(ast, ["VarIn", [["t", ["Number", "1"]]], ["Variable", "y"]])
    ast = next(p.parse("def foo(x y) var t = x, p = y + 1 in y"))
    _assert_body(
        ast,
        [
            "VarIn",
            [["t", ["Variable", "x"]], ["p", ["Binop", "+", ["Variable", "y"], ["Number", "1"]]]],
            ["Variable", "y"],
        ],
    )
