from enum import Enum
from collections import namedtuple


# The lexer returns tokens [0-255] if it is an unknown character,
# otherwise one of these for known things.
class Token(Enum):
    EOF = -1

    # commands
    DEF = -2
    EXTERN = -3

    # primary
    IDENTIFIER = -4
    NUMBER = -5


IdentifierStr = None  # Filled in if Token.IDENTIFIER
NumVal = None  # Filled in if Token.NUMBER


def get_tok():
    """ Return the next token from standard input. """
    LastChar = " "

    # Skip any whitespace.
    while LastChar.isspace():
        LastChar = getchar()

    if LastChar.isalpha(): # identifier: [a-zA-Z][a-zA-Z0-9]*
        IdentifierStr = LastChar
        while LastChar.isalnum():
            LastChar = getchar()
            IdentifierStr += LastChar

        if IdentifierStr == "def":
            return Token.DEF
        if IdentifierStr == "extern":
            return Token.EXTERN
        return Token.IDENTIFIER
    
    # FIXME


##


def getchar():
    raise NotImplementedError
