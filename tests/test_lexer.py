try:
    from context import *
except:
    pass

from typing import List

from kal_lexer import Lexer, Token, TokenType

# ref.: https://github.com/eliben/pykaleidoscope/


def _assert_toks(toks: List[Token], tok_type_names: List[str]):
    """ Assert that the list of toks has the given types. """
    assert all(
        [tok.type.name == tok_type_name for tok, tok_type_name in zip(toks, tok_type_names)]
    )


def test_lexer_simple_tokens_and_values():
    l = Lexer("a+1")
    toks = list(l.tokens())
    assert toks[0] == Token(TokenType.IDENTIFIER, "a")
    assert toks[1] == Token(TokenType.OPERATOR, "+")
    assert toks[2] == Token(TokenType.NUMBER, "1")
    assert toks[3] == Token(TokenType.EOF, "")

    l = Lexer(".1519")
    toks = list(l.tokens())
    assert toks[0] == Token(TokenType.NUMBER, ".1519")


def test_token_types():
    l = Lexer("10.1 def der extern foo (")
    _assert_toks(
        toks=list(l.tokens()),
        tok_type_names=[
            "NUMBER",
            "DEF",
            "IDENTIFIER",
            "EXTERN",
            "IDENTIFIER",
            "OPERATOR",
            "EOF",
        ],
    )

    l = Lexer("+- 1 2 22 22.4 a b2 C3d")
    _assert_toks(
        toks=list(l.tokens()),
        tok_type_names=[
            "OPERATOR",
            "OPERATOR",
            "NUMBER",
            "NUMBER",
            "NUMBER",
            "NUMBER",
            "IDENTIFIER",
            "IDENTIFIER",
            "IDENTIFIER",
            "EOF",
        ],
    )


def test_skip_whitespace_comments():
    l = Lexer(
        """
        def foo # this is a comment
        # another comment
        \t\t\t10
        """
    )
    _assert_toks(toks=list(l.tokens()), tok_type_names=["DEF", "IDENTIFIER", "NUMBER", "EOF"])
