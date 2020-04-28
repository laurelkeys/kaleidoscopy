from ctypes import CFUNCTYPE, c_double
from typing import Dict, List, Iterator, Optional
from collections import namedtuple

import llvmlite.binding as llvm

from termcolor import colored

import kal_ast

from kal_ir import GenerateCodeError, LLVMCodeGenerator
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope
#       https://github.com/frederickjeanguerin/pykaleidoscope


EvalResult = namedtuple(
    typename="EvalResult", field_names=["value", "ast", "unoptimized_ir", "optimized_ir"],
)


class KaleidoscopeCodeEvaluator:
    """ Evaluator for Kaleidoscope expressions.

        Once an object is created, calls to `evaluate()` add new expressions to the module.\n
        Definitions (including 'extern's) are only added into the IR, no JIT compilation occurs.\n
        When a top-level expression is evaluated, the whole module is JITed and the result of the expression is returned.
    """

    def __init__(self):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        # llvm.initialize_native_asmparser()

        self.code_generator = LLVMCodeGenerator()

        self.target = llvm.Target.from_default_triple()

    def reset(self, history: Optional[List[kal_ast.Node]] = None) -> bool:
        self.code_generator = LLVMCodeGenerator()
        if history is not None:
            try:
                for ast in history:
                    self._evaluate_ast(ast)
                return True
            except GenerateCodeError:
                return False

    def evaluate(self, kal_code: str, options: Dict[str, bool] = None) -> Optional[float]:
        # NOTE since Kaleidoscope only deals with doubles, return types are always 'float'
        return next(self._evaluate(kal_code, options or {})).value

    def _evaluate(self, kal_code: str, options: Dict[str, bool]) -> Iterator[EvalResult]:
        """ Evaluates the given Kaleidoscope code `kal_code`.

            Returns an `EvalResult` with the result accessible in `.value`.\n
            Return value is `None` for definitions and 'extern's, and the evaluated expression value for top-level expressions.
        """
        # Parse the given Kaleidoscope code and generate LLVM IR code from it
        for ast in Parser().parse(kal_code):
            # FIXME `options` may make the `.value` result a `str` instead of a `float`
            yield self._evaluate_ast(ast, **options)

    def _evaluate_ast(
        self,
        ast: kal_ast.Node,
        optimize=True,
        llvmdump=False,
        noexec=False,
        parseonly=False,
        verbose=False,
    ) -> Iterator[EvalResult]:
        """ Evaluates a single top-level expression represented by `ast`.

            Returns an `EvalResult` with the result accessible in `.value`.

            - `optimize`: enable LLVM optimization passes
            - `llvmdump`: dump generated LLVM IR code prior to execution
            - `noexec`: generate code but don't execute it (note: yields unoptimized IR)
            - `parseonly`: simply parse the code (note: yields a string representation of the AST)
            - `verbose`: yields a quadruple with: result value, AST, unoptimized IR, optimized IR
        """
        if parseonly:
            return EvalResult(value=str(ast), ast=ast, unoptimized_ir=None, optimized_ir=None)

        # Generate LLVM IR code from the AST representation of the code
        self.code_generator.generate_code(ast)

        if noexec:
            return EvalResult(
                value=str(self.code_generator.module).split("\n\n")[-1],
                ast=ast,
                unoptimized_ir=None,
                optimized_ir=None,
            )

        raw_ir = None
        if verbose:
            raw_ir = str(self.code_generator.module).split("\n\n")[-1]

        if llvmdump:
            with open("__dump__unoptimized.ll", "w") as dump:
                dump.write(str(self.code_generator.module))
                print(
                    colored(f"Unoptimized LLVM IR code dumped to '{dump.name}'", color="yellow",)
                )

        # If we're evaluating an anonymous wrapper for a top-level expression,
        # JIT-compile the module and run the function to get its result
        is_def_or_extern = not (isinstance(ast, kal_ast.Function) and ast.is_anonymous())

        # If we're evaluating a definition or extern declaration, don't do anything else
        if is_def_or_extern and not verbose:
            return EvalResult(value=None, ast=ast, unoptimized_ir=raw_ir, optimized_ir=None)

        # Convert LLVM IR into in-memory representation and verify the code
        llvmmod: llvm.ModuleRef = llvm.parse_assembly(str(self.code_generator.module))
        llvmmod.verify()

        # Run module optimization passes
        if optimize:
            pmb = llvm.create_pass_manager_builder()
            pmb.opt_level = 2
            pm = llvm.create_module_pass_manager()
            pmb.populate(pm)
            pm.run(llvmmod)

            if llvmdump:
                with open("__dump__optimized.ll", "w") as dump:
                    dump.write(str(llvmmod))
                    print(
                        colored(
                            f"Optimized LLVM IR code dumped to '{dump.name}'", color="yellow",
                        )
                    )

        opt_ir = None
        if verbose:
            opt_ir = str(self.code_generator.module).split("\n\n")[-2]
            if is_def_or_extern:
                return EvalResult(value=None, ast=ast, unoptimized_ir=raw_ir, optimized_ir=opt_ir)

        # NOTE a execution_engine takes ownership of target_machine, so it
        # has to be recreated anew each time we call create_mcjit_compiler
        target_machine = self.target.create_target_machine()
        with llvm.create_mcjit_compiler(llvmmod, target_machine) as execution_engine:
            execution_engine.finalize_object()

            if llvmdump:
                with open("__dump__assembler.asm", "w") as dump:
                    dump.write(target_machine.emit_assembly(llvmmod))
                    print(colored(f"Machine code dumped to '{dump.name}'", color="yellow"))

            fn_ptr = CFUNCTYPE(c_double)(execution_engine.get_function_address(ast.proto.name))

            result = fn_ptr()
            return EvalResult(value=result, ast=ast, unoptimized_ir=raw_ir, optimized_ir=opt_ir)
