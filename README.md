# kaleidoscopy

## Grammar
```
numberexpr ::= number

parenexpr ::= '(' expression ')'

identifierexpr
  ::= identifier
  ::= identifier '(' expression* ')'

primary
  ::= identifierexpr
  ::= numberexpr
  ::= parenexpr

expression ::= primary binoprhs

binop ::= '<' | '+' | '-' | '*'

binoprhs ::= (binop primary)*

prototype ::= id '(' id* ')'

definition ::= 'def' prototype expression

external ::= 'extern' prototype

top ::= definition | external | expression | ';'
```

## References
- [LLVM Language Reference Manual](http://llvm.org/docs/LangRef.html)
- ["Kaleidoscope" language](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/LangImpl01.html), from the [LLVM Tutorial](http://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html)
- [frederickjeanguerin](https://github.com/frederickjeanguerin)'s [pykaleidoscope](https://github.com/frederickjeanguerin/pykaleidoscope)
- [eliben](https://github.com/eliben)'s [pykaleidoscope](https://github.com/eliben/pykaleidoscope)