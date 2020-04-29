# kaleidoscopy

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

identifierexpr ::= identifier
                 | identifier '(' expression* ')'

numberexpr ::= number

parenexpr ::= '(' expression ')'

ifexpr ::= 'if' expression 'then' expression 'else' expression

forexpr ::= 'for' identifier '=' expr ',' expr (',' expr)? 'in' expression
```

## References
- ["Kaleidoscope" language](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/LangImpl01.html), from the [LLVM Tutorial](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html)
- [frederickjeanguerin](https://github.com/frederickjeanguerin)'s [pykaleidoscope](https://github.com/frederickjeanguerin/pykaleidoscope)
- [eliben](https://github.com/eliben)'s [pykaleidoscope](https://github.com/eliben/pykaleidoscope)