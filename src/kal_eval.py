from ctypes import CFUNCTYPE, c_double
from typing import Dict, List, Iterator, Optional
from collections import namedtuple

import llvmlite.ir as ir
import llvmlite.binding as llvm

from termcolor import colored

import kal_ast

from kal_ir import GenerateCodeError, LLVMCodeGenerator
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope
#       https://github.com/frederickjeanguerin/pykaleidoscope


EvalResult = namedtuple(
    typename="EvalResult", field_names=["ast", "unoptimized_ir", "optimized_ir", "value"]
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

        self.target = llvm.Target.from_default_triple()
        self.reset()

    def __add_built_ins(self):
        """ Add `putchard()`. """
        # ref.: https://github.com/eliben/pykaleidoscope

        # Add the declaration of putchar
        putchar = ir.Function(
            self.code_generator.module,
            ftype=ir.FunctionType(return_type=ir.IntType(32), args=[ir.IntType(32)]),
            name="putchar",
        )

        # Add putchard
        putchard = ir.Function(
            self.code_generator.module,
            ftype=ir.FunctionType(return_type=ir.DoubleType(), args=[ir.DoubleType()]),
            name="putchard",
        )

        builder = ir.IRBuilder(block=putchard.append_basic_block("entry"))
        int_value = builder.fptoui(putchard.args[0], ir.IntType(32), "intcast")
        builder.call(fn=putchar, args=[int_value])
        builder.ret(value=ir.Constant(ir.DoubleType(), 0.0))

    def __last_ir(self, index: int = -1) -> str:
        """ Returns the last bunch of code added to `self.code_generator.module`.
            Thus, this gets the lastly generated IR for the top-level expression.
        """
        # ref.: https://github.com/frederickjeanguerin/pykaleidoscope
        return str(self.code_generator.module).split("\n\n")[index]

    def __dump(self, text, into, and_log=None):
        """ Create a file named `into` and dump `text` into it. """
        with open(into, "w") as dump:
            dump.write(str(text))
            print(colored(f"{and_log} dumped to '{dump.name}'", color="yellow"))

    def reset(self, history: Optional[List[kal_ast.Node]] = None) -> bool:
        self.code_generator = LLVMCodeGenerator()
        self.__add_built_ins()
        if history is not None:
            try:
                for ast in history:
                    self._eval_ast(ast)
            except GenerateCodeError:
                return False
        return True  # successfully reset

    def eval_expr(self, kal_code: str, options: Dict[str, bool] = None) -> Optional[float]:
        # NOTE since Kaleidoscope only deals with doubles, return types are always 'float'
        # FIXME depending on `options`, `value` may result in a 'str' instead of a 'float'
        """ Evaluates only the first top-level expression in `kal_code`. """
        return next(self.eval(kal_code, options or {})).value

    def eval(self, kal_code: str, options: Dict[str, bool]) -> Iterator[EvalResult]:
        """ Iterator that evaluates the given Kaleidoscope code `kal_code`.

            Yields an `EvalResult` with the result accessible in `.value`.\n
            Note: `.value` is `None` for definitions and 'extern's, and the evaluated expression value for top-level expressions.
        """
        # Parse the given Kaleidoscope code and generate LLVM IR from it
        for ast in Parser().parse(kal_code):
            yield self._eval_ast(ast, **options)

    def _eval_ast(
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
        raw_ir = None
        opt_ir = None
        if parseonly:
            return EvalResult(ast, raw_ir, opt_ir, value=str(ast))

        # Generate LLVM IR from the AST representation of the code
        self.code_generator.generate_code(ast)

        raw_ir = self.__last_ir()

        if noexec:
            return EvalResult(ast, raw_ir, opt_ir, value=raw_ir)

        # If we're evaluating a definition or extern declaration, don't do anything else
        # If it's an anonymous wrapper, JIT-compile the module and run the function to get its result
        is_def_or_extern = not (isinstance(ast, kal_ast.Function) and ast.is_anonymous())
        if is_def_or_extern and not optimize:
            return EvalResult(ast, raw_ir, opt_ir, value=None)

        # Convert LLVM IR into in-memory representation and verify the code
        llvmmod: llvm.ModuleRef = llvm.parse_assembly(llvmir=str(self.code_generator.module))
        llvmmod.verify()

        if llvmdump:
            self.__dump(llvmmod, into="__dump__unoptimized.ll", and_log="Unoptimized LLVM IR code")

        # Run module optimization passes
        if optimize:
            pmb = llvm.create_pass_manager_builder()
            pm = llvm.create_module_pass_manager()

            # pm.add_instruction_combining_pass()
            # pm.add_gvn_pass()
            # pm.add_cfg_simplification_pass()
            # pm.add_dead_code_elimination_pass()

            pmb.opt_level = 2
            pmb.populate(pm)
            pm.run(llvmmod)
            # FIXME make sure all optimizations at InitializeModuleAndPassManager() are enabled

            if llvmdump:
                self.__dump(llvmmod, into="__dump__optimized.ll", and_log="Optimized LLVM IR code")

            opt_ir = self.__last_ir(index=-2)

        if is_def_or_extern:
            return EvalResult(ast, raw_ir, opt_ir, value=None)

        # Create a MCJIT execution engine to JIT-compile the module
        # NOTE a execution_engine takes ownership of target_machine, so it
        # has to be recreated anew each time we call create_mcjit_compiler
        target_machine = self.target.create_target_machine()
        with llvm.create_mcjit_compiler(llvmmod, target_machine) as execution_engine:
            execution_engine.finalize_object()

            if llvmdump:
                self.__dump(
                    target_machine.emit_assembly(llvmmod),
                    into="__dump__assembler.asm",
                    and_log="Machine code",
                )

            fn_ptr = CFUNCTYPE(c_double)(execution_engine.get_function_address(ast.proto.name))
            result = fn_ptr()

            return EvalResult(ast, raw_ir, opt_ir, value=result)

    def compile_to_object_code(self):
        """ Compile the previously evaluated code into an object file for the native target.
            Returns its contents as a byte string.
        """
        # ref.: https://github.com/eliben/pykaleidoscope/
        target_machine: llvm.TargetMachine = self.target.create_target_machine(codemodel="small")

        # Convert LLVM IR into in-memory representation
        llvmmod: llvm.ModuleRef = llvm.parse_assembly(llvmir=str(self.code_generator.module))
        return target_machine.emit_object(llvmmod)
