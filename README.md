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

expression ::= primary binoprhs

binoprhs ::= (binop primary)*

binop ::= '<'
        | '+'
        | '-'
        | '*'

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

<!-- FIXME replace `id` by `identifier` here and in the code -->

## References
- [LLVM Language Reference Manual](http://llvm.org/docs/LangRef.html)
- ["Kaleidoscope" language](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/LangImpl01.html), from the [LLVM Tutorial](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html)
- [frederickjeanguerin](https://github.com/frederickjeanguerin)'s [pykaleidoscope](https://github.com/frederickjeanguerin/pykaleidoscope)
- [eliben](https://github.com/eliben)'s [pykaleidoscope](https://github.com/eliben/pykaleidoscope)