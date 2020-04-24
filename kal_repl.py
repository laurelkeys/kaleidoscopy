import os
import sys

import kal_lexer
import kal_parser


# Top-Level parsing
def HandleDefinition():
    if kal_parser.parse_Definition():
        print("Parsed a function definition.\n")
    else:
        # Skip token for error recovery.
        kal_parser.get_next_token()


def HandleExtern():
    if kal_parser.parse_Extern():
        print("Parsed an extern\n")
    else:
        # Skip token for error recovery.
        kal_parser.get_next_token()


def HandleTopLevelExpression():
    # Evaluate a top-level expression into an anonymous function.
    if kal_parser.parse_TopLevelExpr():
        print("Parsed a top-level expr\n")
    else:
        # Skip token for error recovery.
        kal_parser.get_next_token()


# The Driver
def MainLoop():
    """ top ::= definition | external | expression | ';' """
    while True:
        print("ready> ")
        if kal_parser.CurTok == kal_lexer.Token.EOF:
            return
        elif kal_parser.CurTok == ";":  # ignore top-level semicolons.
            kal_parser.get_next_token()
        elif kal_parser.CurTok == kal_lexer.Token.DEF:
            HandleDefinition()
        elif kal_parser.CurTok == kal_lexer.Token.EXTERN:
            HandleExtern()
        else:
            HandleTopLevelExpression()


# Main driver code.
if __name__ == "__main__":

    # Prime the first token.
    print("ready> ")
    kal_parser.get_next_token()

    # Run the main "interpreter loop" now.
    MainLoop()
