from enum import Enum
from typing import Dict
from collections import namedtuple


class Associativity(Enum):
    NON = 0
    LEFT = 1
    RIGHT = 2


OperatorInfo = namedtuple(typename="Operator", field_names=["associativity", "precedence"])


DEFAULT_PRECEDENCE = 30  # used for user-defined binary operators


operators: Dict[str, OperatorInfo] = {
    # lowest precedence
    "<": OperatorInfo(Associativity.LEFT, precedence=10),
    "+": OperatorInfo(Associativity.LEFT, precedence=20),
    "-": OperatorInfo(Associativity.LEFT, precedence=20),
    "*": OperatorInfo(Associativity.LEFT, precedence=40),
    # highest precedence
}
assert all([op.precedence >= 1 for op in operators.values()]), "1 is lowest definable precedence"


def get_precedence(op: str) -> int:
    if (op_info := operators.get(op)) is not None:
        return op_info.precedence
    return -1  # non-operator (special value)


def get_associativity(op: str) -> int:
    if (op_info := operators.get(op)) is not None:
        return op_info.associativity
    return Associativity.NON  # non-operator
