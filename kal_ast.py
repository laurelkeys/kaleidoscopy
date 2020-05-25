from __future__ import annotations

from typing import List, Tuple

import kal_ops


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


class VarExpr(Expr):
    """ Expression class for var/in. """

    def __init__(self, vars_init_list: List[Tuple[str, Expr]], body: Expr):
        self.vars_init_list = vars_init_list
        self.body = body


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


class UnaryExpr(Expr):
    """ Expression class for a unary operator. """

    def __init__(self, op: str, operand: Expr):
        self.op = op
        self.operand = operand


class CallExpr(Expr):
    """ Expression class for function calls. """

    def __init__(self, callee: str, args: List[Expr]):
        self.callee = callee
        self.args = args


class IfExpr(Expr):
    """ Expression class for if/then/else.

        if `cond_expr` then `then_expr` else `else_expr`
    """

    def __init__(self, cond_expr: Expr, then_expr: Expr, else_expr: Expr):
        self.cond_expr = cond_expr
        self.then_expr = then_expr
        self.else_expr = else_expr


class ForExpr(Expr):
    """ Expression class for for/in.

        for `id_name` = `init_expr`, `cond_expr`, `step_expr` in `body_expr`
    """

    def __init__(
        self, id_name: str, init_expr: Expr, cond_expr: Expr, step_expr: Expr, body_expr: Expr
    ):
        self.id_name = id_name
        self.init_expr = init_expr
        self.cond_expr = cond_expr
        self.step_expr = step_expr
        self.body_expr = body_expr


class Prototype(Node):
    """ This class represents the \"prototype\" for a function, which captures its name,
        and its argument names (thus, implicitly, the number of arguments the function takes).
    """

    def __init__(
        self,
        name: str,
        params: List[str],
        is_operator=False,
        bin_op_precedence=kal_ops.DEFAULT_PRECEDENCE,
    ):
        self.name = name
        self.params = params
        self.is_operator = is_operator
        self.bin_op_precedence = bin_op_precedence
        if is_operator:
            if len(params) == 1:
                assert self.name.startswith("unary")
            elif len(params) == 2:
                assert self.name.startswith("binary")
            else:
                assert False, f"Invalid operator `{name}`"

    def is_unary_operator(self):
        return self.is_operator and len(self.params) == 1

    def is_binary_operator(self):
        return self.is_operator and len(self.params) == 2

    def get_binary_precedence(self):
        assert self.is_binary_operator()
        return self.bin_op_precedence

    def get_operator_name(self):
        assert self.is_operator
        return self.name[-1]  # NOTE only single-character user-defined operators are allowed

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
