from __future__ import annotations

from typing import List


class Node:
    """ Base class for all AST nodes. """

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            + ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
            + ")"
        )

    def __repr__(self):
        return str(self)


class Expr(Node):
    """ Base class for all expression nodes. """

    pass


class NumberExpr(Expr):
    """ Expression class for numeric literals, like `1.0`. """

    def __init__(self, val: str):
        self.val = val


class VariableExpr(Expr):
    """ Expression class for referencing a variable, like `a`. """

    def __init__(self, name: str):
        self.name = name


class BinaryExpr(Expr):
    """ Expression class for a binary operator. """

    def __init__(self, op: str, lhs: Expr, rhs: Expr):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class CallExpr(Expr):
    """ Expression class for function calls. """

    def __init__(self, callee: str, args: List[Expr]):
        self.callee = callee
        self.args = args


class IfExpr(Expr):
    """ Expression class for if/then/else. """

    def __init__(self, cond_expr: Expr, then_expr: Expr, else_expr: Expr):
        self.cond_expr = cond_expr
        self.then_expr = then_expr
        self.else_expr = else_expr


class Prototype(Node):
    """ This class represents the \"prototype\" for a function, which captures its name,
        and its argument names (thus implicitly the number of arguments the function takes).
    """

    def __init__(self, name: str, params: List[str]):
        self.name = name
        self.params = params

    # ref.: https://github.com/frederickjeanguerin/pykaleidoscope

    _anonymous_count = 0

    @classmethod
    def Anonymous(cls) -> Prototype:
        """ Create an anonymous function prototype. """
        cls._anonymous_count += 1
        return Prototype(name=f"_anon_fn_{cls._anonymous_count}", params=[])

    def is_anonymous(self) -> bool:
        return self.name.startswith("_anon_fn")


class Function(Node):
    """ This class represents a function definition itself. """

    def __init__(self, proto: Prototype, body: Expr):
        self.proto = proto
        self.body = body

    # ref.: https://github.com/frederickjeanguerin/pykaleidoscope

    @staticmethod
    def Anonymous(body: Expr) -> Function:
        """ Create an anonymous function to hold an expression. """
        return Function(Prototype.Anonymous(), body)

    def is_anonymous(self) -> bool:
        return self.proto.is_anonymous()
