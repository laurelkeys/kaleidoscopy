from ctypes import CFUNCTYPE, c_double
from typing import Any, Optional

import llvmlite.binding as llvm

import kal_ast

from kal_ir import LLVMCodeGenerator
from kal_parser import Parser

# ref.: https://github.com/eliben/pykaleidoscope
#       https://github.com/frederickjeanguerin/pykaleidoscope


class KaleidoscopeCodeEvaluator:
    """ Evaluator for Kaleidoscope expressions.

        Once an object is created, calls to `evaluate()` add new expressions to the module.\n
        Definitions (including `extern`s) are only added into the IR, no JIT compilation occurs.\n
        When a top-level expression is evaluated, the whole module is JITed and the result of the expression is returned.
    """

    def __init__(self):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        self.code_generator = LLVMCodeGenerator()

        self.target = llvm.Target.from_default_triple()

    # FIXME typing
    def evaluate(self, kal_code: str, optimize=True, llvmdump=False) -> Optional[Any]:
        """ Evaluate the given Kaleidoscope code `kal_code`.

            Returns `None` for definitions and `extern`s, and the evaluated expression value for top-level expressions.
        """
        # Parse the given Kaleidoscope code and generate LLVM IR code from it
        ast = next(Parser().parse(kal_code))
        self.code_generator.generate_code(ast)

        if llvmdump:
            print("======== Unoptimized LLVM IR")
            print(str(self.code_generator.module))

        # If we're evaluating a definition or extern declaration, don't do anything else
        if not (isinstance(ast, kal_ast.Function) and ast.is_anonymous()):
            return None

        # If we're evaluating an anonymous wrapper for a top-level expression,
        # JIT-compile the module and run the function to get its result

        # Convert LLVM IR into in-memory representation and verify the code
        llvmmod: llvm.ModuleRef = llvm.parse_assembly(str(self.code_generator.module))
        llvmmod.verify()

        # Optimize the module
        if optimize:
            pmb = llvm.create_pass_manager_builder()
            pmb.opt_level = 2
            pm = llvm.create_module_pass_manager()
            pmb.populate(pm)
            pm.run(llvmmod)

            if llvmdump:
                print("======== Optimized LLVM IR")
                print(str(llvmmod))

        # NOTE a execution_engine takes ownership of target_machine, so it
        # has to be recreated anew each time we call create_mcjit_compiler
        target_machine = self.target.create_target_machine()
        with llvm.create_mcjit_compiler(llvmmod, target_machine) as execution_engine:
            execution_engine.finalize_object()

            if llvmdump:
                print("======== Machine code")
                print(target_machine.emit_assembly(llvmmod))

            fn_ptr = CFUNCTYPE(c_double)(execution_engine.get_function_address(ast.proto.name))

            result = fn_ptr()
            return result
