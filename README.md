# kaleidoscopy
An implementation of the [LLVM Tutorial](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html)'s "[Kaleidoscope](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html)" toy language, using [Python 3.8](requirements.txt) and [llvmlite 0.32](https://github.com/numba/llvmlite).

Based on both [frederickjeanguerin](https://github.com/frederickjeanguerin/pykaleidoscope)'s and [eliben](https://github.com/eliben/pykaleidoscope)'s `pykaleidoscope`.

## Grammar
```
toplevel ::= definition
           | external
           | toplevelexpr
           | ';'

definition ::= 'def' prototype expression

external ::= 'extern' prototype

toplevelexpr ::= expression

prototype ::= identifier '(' identifier* ')'
            | 'binary' LETTER number? '(' identifier identifier ')'
            | 'unary' LETTER '(' identifier ')'

expression ::= unary binoprhs

binoprhs ::= (<binop> unary)*

binop ::= '<'
        | '+'
        | '-'
        | '*'

unary ::= primary
        | <unop> unary

unop ::= '!'

primary ::= identifierexpr
          | numberexpr
          | parenexpr
          | ifexpr
          | forexpr
          | varexpr

identifierexpr ::= identifier
                 | identifier '(' expression* ')'

numberexpr ::= number

parenexpr ::= '(' expression ')'

ifexpr ::= 'if' expression 'then' expression 'else' expression

forexpr ::= 'for' identifier '=' expression
                  ',' expression
                  (',' expression)?
            'in' expression

varexpr ::= 'var' identifier ('=' expression)?
                  (',' identifier ('=' expression)?)*
            'in' expression
```
