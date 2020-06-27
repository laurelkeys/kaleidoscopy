from typing import List, Iterator, Optional

import kal_ast
import kal_ops
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

    def __curr_tok_is_operator(self, operator_value: str) -> bool:
        return self.curr_tok.type == TokenType.OPERATOR and self.curr_tok.value == operator_value

    def __eat_tok(self) -> Token:
        self.curr_tok = next(self.tokens)

    def __try_eat_tok(self, expected_type: TokenType, expected_value: Optional[str] = None) -> Token:
        if expected_type != self.curr_tok.type:
            raise ParseError(f"Expected '{expected_type}'")

        elif expected_type == TokenType.OPERATOR or expected_value is not None:
            if self.curr_tok.value != expected_value:
                raise ParseError(f"Expected '{expected_value}' but got '{self.curr_tok.value}'")

        self.__eat_tok()

    def parse(self, source_code: str) -> Iterator[Optional[kal_ast.Node]]:
        """ Returns the nodes of the AST representation of `source_code`. """
        self.tokens = Lexer(source_code).tokens()
        self.__eat_tok()

        while self.curr_tok.type != TokenType.EOF:
            if (top_level := self._parse_top_level()) is not None:
                yield top_level

    def _parse_top_level(self) -> Optional[kal_ast.Node]:
        """ `toplevel ::= definition
                        | external
                        | toplevelexpr
                        | ';'`
        """
        if self.__curr_tok_is_operator(";"):
            self.__eat_tok()  # ignore top-level semicolons
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
        self.__eat_tok()  # number
        return result

    def _parse_paren_expr(self) -> Optional[kal_ast.Expr]:
        """ `parenexpr ::= '(' expression ')'` """
        self.__eat_tok()  # '('
        expr = self._parse_expression()
        self.__try_eat_tok(TokenType.OPERATOR, expected_value=")")  # ')'
        return expr

    def _parse_identifier_expr(self) -> Optional[kal_ast.Expr]:
        """ `identifierexpr ::= identifier
                              |  identifier '(' expression* ')'`
        """
        id_name = self.curr_tok.value
        self.__eat_tok()  # identifier

        # Simple variable ref
        if not self.__curr_tok_is_operator("("):
            return kal_ast.VariableExpr(id_name)

        # Function call
        self.__eat_tok()  # '('
        args: List[kal_ast.Expr] = []
        if not self.__curr_tok_is_operator(")"):
            while True:
                args.append(self._parse_expression())
                if self.__curr_tok_is_operator(")"):
                    break
                self.__try_eat_tok(TokenType.OPERATOR, expected_value=",")  # ','
        self.__eat_tok()  # ')'
        return kal_ast.CallExpr(id_name, args)

    def _parse_primary(self) -> Optional[kal_ast.Expr]:
        """ `primary ::= identifierexpr
                       | numberexpr
                       | parenexpr
                       | ifexpr
                       | forexpr
                       | varexpr`
        """
        if self.curr_tok.type == TokenType.IDENTIFIER:
            return self._parse_identifier_expr()

        elif self.curr_tok.type == TokenType.NUMBER:
            return self._parse_number_expr()

        elif self.__curr_tok_is_operator("("):
            return self._parse_paren_expr()

        elif self.curr_tok.type == TokenType.IF:
            return self._parse_if_expr()

        elif self.curr_tok.type == TokenType.FOR:
            return self._parse_for_expr()

        elif self.curr_tok.type == TokenType.VAR:
            return self._parse_var_expr()

        raise ParseError(f"Unknown token '{self.curr_tok.value}' when expecting an expression")

    def _parse_expression(self) -> Optional[kal_ast.Expr]:
        """ `expression ::= unary binoprhs` """
        lhs = self._parse_unary()
        # NOTE start with precedence 0, because we want to
        # bind any operator to the expression at this point
        return self._parse_bin_op_rhs(expr_prec=0, lhs=lhs)

    def _parse_bin_op_rhs(self, expr_prec: int, lhs: kal_ast.Expr) -> Optional[kal_ast.Expr]:
        """ `binoprhs ::= (<binop> unary)*`

            Note: `expr_prec` is the minimum precedence to keep going (precedence climbing).
        """
        while True:
            # If this is a binary operator that binds at least as tightly as the
            # currently parsed sub-expression, consume it, otherwise we are done
            if (curr_prec := self.__curr_tok_precedence()) < expr_prec:
                # NOTE the precedence of non-operators is defined to be -1,
                # so this condition handles cases when the expression has ended
                return lhs

            bin_op = self.curr_tok.value
            self.__eat_tok()  # <binop>
            rhs = self._parse_unary()

            # If bin_op binds less tightly with RHS than the operator
            # after RHS, let the pending operator take RHS as its LHS
            if curr_prec < (_next_prec := self.__curr_tok_precedence()):
                rhs = self._parse_bin_op_rhs(curr_prec + 1, rhs)

            # Merge LHS/RHS
            lhs = kal_ast.BinaryExpr(bin_op, lhs, rhs)

    def _parse_unary(self) -> Optional[kal_ast.Expr]:
        """ `unary ::= primary
                     | <unop> unary`
        """
        # If the current token is not an operator, it must be a primary expression
        if not self.curr_tok.type == TokenType.OPERATOR or self.curr_tok.value in ["(", ","]:
            return self._parse_primary()

        # Unary operator
        un_op = self.curr_tok.value
        self.__eat_tok()  # <unop>
        return kal_ast.UnaryExpr(op=un_op, operand=self._parse_unary())

    def _parse_if_expr(self) -> Optional[kal_ast.Expr]:
        """ `ifexpr ::= 'if' expression 'then' expression 'else' expression` """
        self.__eat_tok()  # 'if'
        cond_expr = self._parse_expression()

        self.__try_eat_tok(TokenType.THEN, expected_value="then")  # 'then'
        then_expr = self._parse_expression()

        self.__try_eat_tok(TokenType.ELSE, expected_value="else")  # 'else'
        else_expr = self._parse_expression()

        return kal_ast.IfExpr(cond_expr, then_expr, else_expr)

    def _parse_for_expr(self) -> Optional[kal_ast.Expr]:
        """ `forexpr ::= 'for' identifier '=' expression ',' expression (',' expression)? 'in' expression` """
        self.__eat_tok()  # 'for'

        id_name = self.curr_tok.value
        self.__try_eat_tok(TokenType.IDENTIFIER)  # identifier
        self.__try_eat_tok(TokenType.OPERATOR, expected_value="=")  # '='
        init_expr = self._parse_expression()

        self.__try_eat_tok(TokenType.OPERATOR, expected_value=",")  # ','
        cond_expr = self._parse_expression()

        step_expr = None  # the step value is optional
        if self.__curr_tok_is_operator(","):
            self.__eat_tok()  # ','
            step_expr = self._parse_expression()

        self.__try_eat_tok(TokenType.IN)  # 'in'
        body_expr = self._parse_expression()

        return kal_ast.ForExpr(id_name, init_expr, cond_expr, step_expr, body_expr)

    def _parse_var_expr(self) -> Optional[kal_ast.Expr]:
        """ `varexpr ::= 'var' identifier ('=' expression)?
                               (',' identifier ('=' expression)?)* 'in' expression`
        """
        self.__eat_tok()  # 'var'

        # At least one variable name is required
        if self.curr_tok.type != TokenType.IDENTIFIER:
            raise ParseError("Expected identifier after 'var'")

        var_names = []
        while True:
            # Parse the name and the optional initializer
            name = self.curr_tok.value
            self.__eat_tok()  # identifier
            init = None
            if self.__curr_tok_is_operator("="):
                self.__eat_tok()  # '='
                init = self._parse_expression()
            var_names.append((name, init))

            # If there are no more vars, we're done
            if not self.__curr_tok_is_operator(","):
                break

            self.__eat_tok()  # ','
            if self.curr_tok.type != TokenType.IDENTIFIER:
                raise ParseError("Expected identifier in 'var' after ','")

        self.__try_eat_tok(TokenType.IN)  # 'in'
        body_expr = self._parse_expression()

        return kal_ast.VarInExpr(var_names, body_expr)

    def _parse_prototype(self) -> Optional[kal_ast.Prototype]:
        """ `prototype ::= identifier '(' identifier* ')'
                         | 'binary' LETTER number? '(' identifier identifier ')'
                         | 'unary' LETTER '(' identifier ')'`
        """
        if self.curr_tok.type == TokenType.IDENTIFIER:
            fn_name = self.curr_tok.value
            self.__eat_tok()  # identifier
            params: List[str] = self.__parse_prototype_params()
            return kal_ast.Prototype(fn_name, params)

        # User-defined operators
        elif self.curr_tok.type == TokenType.BINARY:
            return self.__parse_prototype_for_user_def_bin_op()
        elif self.curr_tok.type == TokenType.UNARY:
            return self.__parse_prototype_for_user_def_un_op()

        raise ParseError("Expected function name in prototype")

    def __parse_prototype_params(self) -> List[str]:
        """ Helper for parsing `'(' identifier* ')'`. """
        self.__try_eat_tok(TokenType.OPERATOR, expected_value="(")  # '('

        # Read the list of argument names
        params: List[str] = []
        while self.curr_tok.type == TokenType.IDENTIFIER:
            params.append(self.curr_tok.value)
            self.__eat_tok()  # identifier
        self.__try_eat_tok(TokenType.OPERATOR, expected_value=")")  # ')'

        return params

    def __parse_prototype_for_user_def_bin_op(self) -> Optional[kal_ast.Prototype]:
        """ Helper for parsing `'binary' LETTER number? '(' identifier identifier ')'`. """
        self.__eat_tok()  # 'binary'
        if self.curr_tok.type != TokenType.OPERATOR:
            raise ParseError("Expected operator after 'binary'")
        fn_name = f"binary{self.curr_tok.value}"
        self.__eat_tok()  # LETTER

        # Read the precedence, if present
        precedence = kal_ops.DEFAULT_PRECEDENCE
        if self.curr_tok.type == TokenType.NUMBER:
            precedence = int(self.curr_tok.value)
            if not (1 <= precedence <= 100):
                raise ParseError(f"Invalid precedence: {precedence} (must be in 1..100)")
            self.__eat_tok()  # number

        # As this is a new binary operator, install it
        operators[fn_name[-1]] = kal_ops.OperatorInfo(
            kal_ops.Associativity.NON, precedence  # FIXME associativty
        )

        params: List[str] = self.__parse_prototype_params()
        if len(params) != 2:
            raise ParseError("Expected binary operator to have two operands")

        return kal_ast.Prototype(fn_name, params, is_operator=True, bin_op_precedence=precedence)

    def __parse_prototype_for_user_def_un_op(self) -> Optional[kal_ast.Prototype]:
        """ Helper for parsing `'unary' LETTER '(' identifier ')'`. """
        self.__eat_tok()  # 'unary'
        if self.curr_tok.type != TokenType.OPERATOR:
            raise ParseError("Expected operator after 'unary'")
        fn_name = f"unary{self.curr_tok.value}"
        self.__eat_tok()  # LETTER

        params: List[str] = self.__parse_prototype_params()
        if len(params) != 1:
            raise ParseError("Expected unary operator to have one operand")

        return kal_ast.Prototype(fn_name, params, is_operator=True)

    def _parse_definition(self) -> Optional[kal_ast.Function]:
        """ `definition ::= 'def' prototype expression` """
        self.__eat_tok()  # 'def'
        proto = self._parse_prototype()
        expr = self._parse_expression()
        return kal_ast.Function(proto, body=expr)

    def _parse_external(self) -> Optional[kal_ast.Prototype]:
        """ `external ::= 'extern' prototype` """
        self.__eat_tok()  # 'extern'
        return self._parse_prototype()

    def _parse_top_level_expr(self) -> Optional[kal_ast.Function]:
        """ `toplevelexpr ::= expression` """
        if (expr := self._parse_expression()) is not None:
            # Make an anonymous function prototype for top-level expressions
            return kal_ast.Function.Anonymous(body=expr)
        return None
