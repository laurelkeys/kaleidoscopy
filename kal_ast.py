from typing import List


class ExprAST:
    """ Base class for all expression nodes. """

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            + ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
            + ")"
        )

    def __str__(self):
        return f"{{{self.__class__.__name__}}}"


class NumberExprAST(ExprAST):
    """ Expression class for numeric literals, like `1.0`. """

    def __init__(self, val: float):
        self.val = val


class VariableExprAST(ExprAST):
    """ Expression class for referencing a variable, like `a`. """

    def __init__(self, name: str):
        self.name = name


class BinaryExprAST(ExprAST):
    """ Expression class for a binary operator. """

    def __init__(self, op: str, lhs: ExprAST, rhs: ExprAST):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class CallExprAST(ExprAST):
    """ Expression class for function calls. """

    def __init__(self, callee: str, args: List[ExprAST]):
        self.callee = callee
        self.args = args


class PrototypeAST:
    """ This class represents the \"prototype\" for a function, which captures its name, 
        and its argument names (thus implicitly the number of arguments the function takes).
    """

    def __init__(self, name: str, args: List[str]):
        self.name = name
        self.args = args


class FunctionAST:
    """ This class represents a function definition itself. """

    def __init__(self, proto: PrototypeAST, body: ExprAST):
        self.proto = proto
        self.body = body
