from enum import Enum, unique
from typing import Dict, Iterator
from collections import namedtuple


@unique
class TokenType(Enum):
    EOF = -1

    # commands
    DEF = -2
    EXTERN = -3

    # primary
    IDENTIFIER = -4
    NUMBER = -5

    # control
    IF = -6
    THEN = -7
    ELSE = -8
    FOR = -9
    IN = -10

    # mutable variable definition
    VAR = -11

    # operators
    OPERATOR = -12  # unknown character
    BINARY = -13
    UNARY = -14


Token = namedtuple(typename="Token", field_names=["type", "value"])


keywords: Dict[str, Token] = {
    "def": Token(TokenType.DEF, value="def"),
    "extern": Token(TokenType.EXTERN, value="extern"),
    "if": Token(TokenType.IF, value="if"),
    "then": Token(TokenType.THEN, value="then"),
    "else": Token(TokenType.ELSE, value="else"),
    "for": Token(TokenType.FOR, value="for"),
    "in": Token(TokenType.IN, value="in"),
    "var": Token(TokenType.VAR, value="var"),
    "binary": Token(TokenType.BINARY, value="binary"),
    "unary": Token(TokenType.UNARY, value="unary"),
}
assert all([kw_key == kw.value for kw_key, kw in keywords.items()])
assert len(kw_types := [kw.type for kw in keywords.values()]) == len(set(kw_types))


class Lexer:
    """ Lexer for the Kaleidoscope language. """

    def __init__(self, source_code: str):
        assert len(source_code) > 0
        self.source_code = source_code
        self.last_char = source_code[0]
        self.pos = 0  # index of last_char on source_code

    def __advance_last_char(self) -> str:
        try:
            self.pos += 1
            self.last_char = self.source_code[self.pos]
        except IndexError:
            self.last_char = ""

    def tokens(self) -> Iterator[Token]:
        while self.last_char:
            # Skip any whitespace
            while self.last_char.isspace():
                self.__advance_last_char()

            # Indentifier or keyword: [_a-zA-Z][_a-zA-Z0-9]*
            if self.last_char.isalpha():
                id_str = ""
                while self.last_char.isalnum() or self.last_char == "_":
                    id_str += self.last_char
                    self.__advance_last_char()
                try:
                    yield keywords[id_str]
                except KeyError:
                    yield Token(TokenType.IDENTIFIER, value=id_str)

            # Number: [0-9.]+
            elif self.last_char.isdigit() or self.last_char == ".":
                num_str = ""
                while self.last_char.isdigit() or self.last_char == ".":
                    num_str += self.last_char
                    self.__advance_last_char()
                yield Token(TokenType.NUMBER, value=num_str)

            # Comment (until end of line): #.*\n
            elif self.last_char == "#":
                self.__advance_last_char()
                while self.last_char and self.last_char not in "\r\n":
                    self.__advance_last_char()

            # Otherwise, just return the character
            elif self.last_char:
                yield Token(type=TokenType.OPERATOR, value=self.last_char)
                self.__advance_last_char()

        yield Token(type=TokenType.EOF, value="")
