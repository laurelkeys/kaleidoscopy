from typing import List


class Node:
    """ Base class for all AST nodes. """

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            + ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
            + ")"
        )

    def __str__(self):
        return f"{{{self.__class__.__name__}}}"


class Expr(Node):
    """ Base class for all expression nodes. """

    pass


class NumberExpr(Expr):
    """ Expression class for numeric literals, like `1.0`. """

    def __init__(self, val: float):
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


class Prototype(Node):
    """ This class represents the \"prototype\" for a function, which captures its name,
        and its argument names (thus implicitly the number of arguments the function takes).
    """

    def __init__(self, name: str, params: List[str]):
        self.name = name
        self.params = params


class Function(Node):
    """ This class represents a function definition itself. """

    def __init__(self, proto: Prototype, body: Expr):
        self.proto = proto
        self.body = body
