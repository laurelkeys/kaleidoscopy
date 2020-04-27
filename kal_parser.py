from typing import List, Iterator, Optional

import kal_ast
import kal_lexer

from kal_ops import operators, get_precedence
from kal_lexer import Lexer, Token, TokenType


class ParseError(Exception):
    pass


class Parser:
    """ Parser for the Kaleidoscope language. """

    def __init__(self):
        self.curr_tok: Token = None
        self.tokens: Iterator[Token] = None

    def __curr_tok_precedence(self) -> int:
        return get_precedence(op=self.curr_tok.value)

    def __curr_tok_is_operator(self, operator: str) -> bool:
        return self.curr_tok.type == TokenType.OPERATOR and self.curr_tok.value == operator

    def parse(self, source_code: str) -> Iterator[Optional[kal_ast.Node]]:
        """ Returns the nodes of the AST representation of `source_code`. """
        self.tokens = Lexer(source_code).tokens()
        self.curr_tok = next(self.tokens)

        while self.curr_tok.type != TokenType.EOF:
            if top_level := self._parse_top_level():
                yield top_level

    def _parse_top_level(self) -> Optional[kal_ast.Node]:
        """ `toplevel ::= definition | external | expression | ';'` """
        if self.__curr_tok_is_operator(";"):
            self.curr_tok = next(self.tokens)  # ignore top-level semicolons
            return None

        elif self.curr_tok.type == TokenType.DEF:
            return self._parse_definition()

        elif self.curr_tok.type == TokenType.EXTERN:
            return self._parse_external()

        else:
            return self._parse_top_level_expr()

    def _parse_number_expr(self) -> Optional[kal_ast.Expr]:
        """ `numberexpr ::= number` """
        result = kal_ast.NumberExpr(self.curr_tok.value)
        self.curr_tok = next(self.tokens)  # eat number
        return result

    def _parse_paren_expr(self) -> Optional[kal_ast.Expr]:
        """ `parenexpr ::= '(' expression ')'` """
        self.curr_tok = next(self.tokens)  # eat '('
        expr = self._parse_expression()
        if not expr:
            return None
        elif not self.__curr_tok_is_operator(")"):
            raise ParseError("Expected ')'")
        self.curr_tok = next(self.tokens)  # eat ')'
        return expr

    def _parse_identifier_expr(self) -> Optional[kal_ast.Expr]:
        """ `identifierexpr ::= identifier |  identifier '(' expression* ')'`
        """
        id_name = self.curr_tok.value
        self.curr_tok = next(self.tokens)  # eat identifier

        # Simple variable ref
        if not self.__curr_tok_is_operator("("):
            return kal_ast.VariableExpr(id_name)

        # Function call
        self.curr_tok = next(self.tokens)  # eat '('
        args: List[kal_ast.Expr] = []
        if not self.__curr_tok_is_operator(")"):
            while True:
                # args.append(self._parse_expression())
                if arg := self._parse_expression():
                    args.append(arg)
                else:
                    return None

                if self.__curr_tok_is_operator(")"):
                    break

                if not self.__curr_tok_is_operator(","):
                    raise ParseError("Expected ')' or ',' in argument list")
                self.curr_tok = next(self.tokens)  # eat ','

        self.curr_tok = next(self.tokens)  # eat ')'
        return kal_ast.CallExpr(id_name, args)

    def _parse_primary(self) -> Optional[kal_ast.Expr]:
        """ `primary ::= identifierexpr | numberexpr | parenexpr` """
        if self.curr_tok.type == TokenType.IDENTIFIER:
            return self._parse_identifier_expr()

        elif self.curr_tok.type == TokenType.NUMBER:
            return self._parse_number_expr()

        elif self.__curr_tok_is_operator("("):
            return self._parse_paren_expr()

        else:
            raise ParseError(
                f"Unknown token '{self.curr_tok.value}' when expecting an expression"
            )

    def _parse_expression(self) -> Optional[kal_ast.Expr]:
        """ `expression ::= primary binoprhs` """
        lhs = self._parse_primary()
        # NOTE Start with precedence 0 because we want to
        # bind any operator to the expression at this point
        return self._parse_bin_op_rhs(expr_prec=0, lhs=lhs)

    def _parse_bin_op_rhs(self, expr_prec: int, lhs: kal_ast.Expr) -> Optional[kal_ast.Expr]:
        """ `binoprhs ::= (binop primary)*`

            Note: `expr_prec` is the minimum precedence to keep going (precedence climbing).
        """
        # If this is a binop, find its precedence
        while True:
            curr_prec = self.__curr_tok_precedence()

            # If this is a binary operator that binds at least as tightly as the
            # currently parsed sub-expression, consume it, otherwise we are done
            if curr_prec < expr_prec:
                # NOTE The precedence of non-operators is defined to be -1,
                # so this condition handles cases when the expression ended
                return lhs

            # Okay, we know this is a binop
            bin_op = self.curr_tok.value
            self.curr_tok = next(self.tokens)  # eat binop

            # Parse the primary expression after the binary operator
            rhs = self._parse_primary()

            # If bin_op binds less tightly with RHS than the operator
            # after RHS, let the pending operator take RHS as its LHS
            next_prec = self.__curr_tok_precedence()
            if curr_prec < next_prec:
                rhs = self._parse_bin_op_rhs(curr_prec + 1, rhs)

            # Merge LHS/RHS
            lhs = kal_ast.BinaryExpr(bin_op, lhs, rhs)

    def _parse_prototype(self) -> Optional[kal_ast.Prototype]:
        """ `prototype ::= id '(' id* ')'` """
        if self.curr_tok.type != TokenType.IDENTIFIER:
            raise ParseError("Expected function name in prototype")

        fn_name = self.curr_tok.value
        self.curr_tok = next(self.tokens)  # eat id

        if not self.__curr_tok_is_operator("("):
            raise ParseError("Expected '(' in prototype")
        self.curr_tok = next(self.tokens)  # eat '('

        # Read the list of argument names
        params: List[str] = []
        while self.curr_tok.type == TokenType.IDENTIFIER:
            params.append(self.curr_tok.value)
            self.curr_tok = next(self.tokens)  # eat id

        if not self.__curr_tok_is_operator(")"):
            raise ParseError("Expected ')' in prototype")
        self.curr_tok = next(self.tokens)  # eat ')'

        return kal_ast.Prototype(fn_name, params)

    def _parse_definition(self) -> Optional[kal_ast.Function]:
        """ `definition ::= 'def' prototype expression` """
        self.curr_tok = next(self.tokens)  # eat 'def'
        proto = self._parse_prototype()
        expr = self._parse_expression()
        return kal_ast.Function(proto, body=expr)

    def _parse_external(self) -> Optional[kal_ast.Prototype]:
        """ `external ::= 'extern' prototype` """
        self.curr_tok = next(self.tokens)  # eat 'extern'
        return self._parse_prototype()

    def _parse_top_level_expr(self) -> Optional[kal_ast.Function]:
        """ `toplevelexpr ::= expression` """
        if expr := self._parse_expression():
            # Make an anonymous function prototype for top-level expressions
            return kal_ast.Function.Anonymous(body=expr)
        return None
