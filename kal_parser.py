from typing import Dict, List, Optional

import kal_ast
import kal_lexer

# CurTok/getNextToken - Provide a simple token buffer.
# CurTok is the current token the parser is looking at.
# getNextToken reads another token from the lexer and updates CurTok with its results.
CurTok = None


def get_next_token():  # FIXME typing
    CurTok = kal_lexer.get_tok()
    return CurTok


# BinopPrecedence - This holds the precedence for each binary operator that is defined.
BinopPrecedence: Dict[str, int] = {
    # 1 is lowest precedence.
    "<": 10,
    "+": 20,
    "-": 20,
    "*": 40,  # highest.
    # ...
}

# GetTokPrecedence - Get the precedence of the pending binary operator token.
def GetTokPrecedence() -> int:
    if not CurTok.isascii():
        return -1

    # Make sure it's a declared binop.
    TokPrec = BinopPrecedence[CurTok]
    if TokPrec <= 0:
        return -1
    return TokPrec


# LogError* - These are little helper functions for error handling.
def LogError(err_str: str) -> Optional[kal_ast.ExprAST]:
    print(f"LogError: {err_str}\n")
    return None


def LogErrorP(err_str: str) -> Optional[kal_ast.PrototypeAST]:
    LogError(err_str)
    return None


def parse_NumberExpr() -> kal_ast.ExprAST:
    """ numberexpr ::= number """
    assert CurTok == kal_lexer.Token.NUMBER
    result = kal_ast.NumberExprAST(kal_lexer.NumVal)
    get_next_token()  # consume the number
    return result


def parse_ParenExpr() -> kal_ast.ExprAST:
    """ parenexpr ::= '(' expression ')' """
    get_next_token()  # eat (.
    v = parse_Expression()
    if not v:
        return None

    if CurTok != ")":
        return LogError("expected ')'")
    get_next_token()  # eat ).
    return v


def parse_IdentifierExpr() -> kal_ast.ExprAST:
    """ identifierexpr
          ::= identifier
          ::= identifier '(' expression* ')'
    """
    assert CurTok == kal_lexer.Token.IDENTIFIER
    id_name = kal_lexer.IdentifierStr

    get_next_token()  # eat identifier.

    if CurTok != ")":  # Simple variable ref.
        return kal_ast.VariableExprAST(id_name)

    # Call.
    get_next_token()
    # eat (
    args: List[kal_ast.ExprAST] = []
    if CurTok != ")":
        while True:
            if arg := parse_Expression():
                args.append(arg)
            else:
                return None

            if CurTok == ")":
                break

            if CurTok != ",":
                return LogError("Expected ')' or ',' in argument list")
            get_next_token()

    # Eat the ')'.
    get_next_token()

    return kal_ast.CallExprAST(id_name, args)


def parse_Primary() -> Optional[kal_ast.ExprAST]:
    """ primary
          ::= identifierexpr
          ::= numberexpr
          ::= parenexpr
    """
    if CurTok == kal_lexer.Token.IDENTIFIER:
        return parse_IdentifierExpr()

    elif CurTok == kal_lexer.Token.NUMBER:
        return parse_NumberExpr()

    elif CurTok == "(":
        return parse_ParenExpr()

    else:
        return LogError("unknown token when expecting an expression")


def parse_Expression() -> Optional[kal_ast.ExprAST]:
    """ expression ::= primary binoprhs """
    lhs = parse_Primary()
    if not lhs:
        return None

    return parse_BinOpRHS(0, lhs)


def parse_BinOpRHS(expr_prec: int, lhs: kal_ast.ExprAST) -> Optional[kal_ast.ExprAST]:
    """ binoprhs ::= ('+' primary)* """
    # If this is a binop, find its precedence.
    while True:
        tok_prec = GetTokPrecedence()

        # If this is a binop that binds at least as tightly as the current binop,
        # consume it, otherwise we are done.
        if tok_prec < expr_prec:
            return lhs

        # Okay, we know this is a binop.
        bin_op = CurTok
        get_next_token()  # eat binop

        # Parse the primary expression after the binary operator.
        rhs = parse_Primary()
        if not rhs:
            return None

        # If bin_op binds less tightly with RHS than the operator after RHS,
        # let the pending operator take RHS as its LHS.
        next_prec = GetTokPrecedence()
        if tok_prec < next_prec:
            rhs = parse_BinOpRHS(tok_prec + 1, rhs)  # FIXME comment the reason for +1
            if not rhs:
                return None

        # Merge LHS/RHS.
        lhs = kal_ast.BinaryExprAST(bin_op, lhs, rhs)


def parse_Prototype() -> Optional[kal_ast.PrototypeAST]:
    """ prototype ::= id '(' id* ')' """
    if CurTok != kal_lexer.Token.IDENTIFIER:
        return LogErrorP("Expected function name in prototype")

    fn_name = kal_lexer.IdentifierStr
    get_next_token()

    if CurTok != "(":
        return LogErrorP("Expected '(' in prototype")

    # Read the list of argument names.
    arg_names: List[str] = []
    while get_next_token() == kal_lexer.Token.IDENTIFIER:
        arg_names.append(kal_lexer.IdentifierStr)
    if CurTok != ")":
        return LogErrorP("Expected ')' in prototype")

    # success.
    get_next_token()  # eat ')'.

    return kal_ast.PrototypeAST(fn_name, arg_names)


def parse_Definition() -> Optional[kal_ast.FunctionAST]:
    """ definition ::= 'def' prototype expression """
    get_next_token()  # eat def.
    proto = parse_Prototype()
    if not proto:
        return None

    if e := parse_Expression():
        return kal_ast.FunctionAST(proto, e)
    return None


def parse_Extern() -> Optional[kal_ast.PrototypeAST]:
    """ external ::= 'extern' prototype """
    get_next_token()  # eat extern.
    return parse_Prototype()


def parse_TopLevelExpr() -> Optional[kal_ast.FunctionAST]:
    """ toplevelexpr ::= expression """
    if e := parse_Expression():
        # Make an anonymous proto.
        proto = kal_ast.PrototypeAST(name="", args=[])
        return kal_ast.FunctionAST(proto, e)
    return None
