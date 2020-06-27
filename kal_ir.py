from typing import Any, Dict

import llvmlite.ir as ir

import kal_ast
import kal_ops


class GenerateCodeError(Exception):
    pass


# NOTE Kaleidoscope uses double precision floating point for all values
ZERO = FALSE = ir.Constant(ir.DoubleType(), 0.0)
ONE = TRUE = ir.Constant(ir.DoubleType(), 1.0)

# NOTE fcmp_ordered means that neither operand can be a QNAN (quite NaN)
# NOTE fcmp_unordered means that either operand may be a QNAN (quite NaN)


class LLVMCodeGenerator:
    """ Node visitor class that generates LLVM IR code.

        Note: each `_emit_<Node>()` method should return an appropriate `ir.Value`.
    """

    def __init__(self):
        # Top-level container of all other LLVM IR objects
        self.module: ir.Module = ir.Module()

        # Current IR builder
        self.builder: ir.IRBuilder = None

        # Manages a symbol table while a function is being code generated
        # Maps var names to its address slot (allocated on the stack with alloca)
        self.func_symtab: Dict[str, ir.AllocaInstr] = {}

    def generate_code(self, node: kal_ast.Node):
        assert isinstance(node, (kal_ast.Prototype, kal_ast.Function))
        return self._emit(node)

    def __alloca(self, var_name: str) -> ir.AllocaInstr:
        """ Create an alloca instruction in the entry block of the current function. """
        with self.builder.goto_entry_block():
            var_addr = self.builder.alloca(typ=ir.DoubleType(), size=None, name=var_name)
        return var_addr

    def _emit(self, node: kal_ast.Node) -> Any:
        """ Visit an AST node and emit its corresponding LLVM IR. """
        method = f"_emit_{node.__class__.__name__}"
        visitor = getattr(self, method)
        return visitor(node)

    def _emit_NumberExpr(self, node: kal_ast.NumberExpr) -> ir.Value:
        return ir.Constant(ir.DoubleType(), float(node.val))

    def _emit_VariableExpr(self, node: kal_ast.VariableExpr) -> ir.Value:
        if (var_addr := self.func_symtab.get(node.name)) is not None:
            return self.builder.load(ptr=var_addr, name=node.name)

        raise GenerateCodeError(f"Unknown variable name '{node.name}'")

    def _emit_BinaryExpr(self, node: kal_ast.BinaryExpr) -> ir.Value:
        # Assignment is handled as a special case
        if node.op == "=":
            if not isinstance(node.lhs, kal_ast.VariableExpr):
                raise GenerateCodeError(f"The LHS of '=' must be a variable")

            lhs_addr = self.func_symtab[node.lhs.name]
            rhs_value = self._emit(node.rhs)
            self.builder.store(value=rhs_value, ptr=lhs_addr)

            return rhs_value

        lhs = self._emit(node.lhs)
        rhs = self._emit(node.rhs)

        if node.op == "+":
            return self.builder.fadd(lhs, rhs, name="addtmp")
        elif node.op == "-":
            return self.builder.fsub(lhs, rhs, name="subtmp")
        elif node.op == "*":
            return self.builder.fmul(lhs, rhs, name="multmp")
        elif node.op == "<":
            # Convert unsigned int 0 or 1 (bool) to double 0.0 or 1.0
            return self.builder.uitofp(
                self.builder.fcmp_unordered("<", lhs, rhs, name="cmptmp"),
                ir.DoubleType(),
                name="booltmp",
            )
        elif (user_def_bin_op_fn := self.module.globals.get(f"binary{node.op}")) is not None:
            # User-defined binary operator
            return self.builder.call(fn=user_def_bin_op_fn, args=[lhs, rhs], name="binop")

        raise GenerateCodeError(f"Unknown binary operator '{node.op}'")

    def _emit_UnaryExpr(self, node: kal_ast.UnaryExpr) -> ir.Value:
        operand = self._emit(node.operand)

        # NOTE there are no pre-defined unary operators (unlike with binary operators)
        if (user_def_un_op_fn := self.module.globals.get(f"unary{node.op}")) is not None:
            # User-defined unary operator
            return self.builder.call(fn=user_def_un_op_fn, args=[operand], name="unop")

        raise GenerateCodeError(f"Unknown unary operator '{node.op}'")

    def _emit_VarInExpr(self, node: kal_ast.VarInExpr) -> ir.Value:
        old_bindings: Dict[str, ir.AllocaInstr] = {}

        # Register all variables and emit their inits before adding them to scope
        # NOTE this prevents the initializer from referencing the variable itself
        for name, init in node.var_names:
            init_value = ZERO if init is None else self._emit(init)
            var_addr = self.__alloca(var_name=name)
            self.builder.store(value=init_value, ptr=var_addr)

            # Remember shadowed variable bindings so we can restore them
            old_bindings[name] = self.func_symtab.get(name)
            self.func_symtab[name] = var_addr

        # Generate code for the body, now that all vars are in scope
        body_value = self._emit(node.body_expr)

        # Pop var/in variables from scope
        for name, _ in node.var_names:
            if (old_binding := old_bindings[name]) is not None:
                self.func_symtab[name] = old_binding
            else:
                del self.func_symtab[name]

        return body_value

    def _emit_IfExpr(self, node: kal_ast.IfExpr) -> ir.Value:
        # Create basic blocks in the current function to express the control flow
        then_bb = self.builder.function.append_basic_block("then")
        else_bb = self.builder.function.append_basic_block("else")
        merge_bb = self.builder.function.append_basic_block("endif")

        # Emit the comparison value and branch to either then_bb or else_bb depending on it
        cond_value = self._emit(node.cond_expr)
        self.builder.cbranch(
            cond=self.builder.fcmp_ordered("!=", lhs=cond_value, rhs=FALSE, name="ifcond"),
            truebr=then_bb,
            falsebr=else_bb,
        )

        # NOTE emission of then_value/else_value can modify the current basic block, so we
        # update then_bb/else_bb for PHI to remember which block the 'then'/'else' ends in

        # Emit the 'then' block
        self.builder.position_at_start(block=then_bb)
        then_value = self._emit(node.then_expr)
        self.builder.branch(target=merge_bb)  # branch to 'endif' after executing 'then'
        then_bb = self.builder.block

        # Emit the 'else' block
        self.builder.position_at_start(block=else_bb)
        else_value = self._emit(node.else_expr)
        self.builder.branch(target=merge_bb)  # branch to 'endif' after executing 'else'
        else_bb = self.builder.block

        # Emit the merge ('endif') block
        self.builder.position_at_start(block=merge_bb)
        phi: ir.PhiInstr = self.builder.phi(typ=ir.DoubleType(), name="iftmp")
        phi.add_incoming(value=then_value, block=then_bb)
        phi.add_incoming(value=else_value, block=else_bb)
        return phi

    def _emit_ForExpr(self, node: kal_ast.ForExpr) -> ir.Value:
        # Create an alloca for the induction variable in the entry block of the current function
        var_addr = self.__alloca(var_name=node.id_name)

        # Emit the initializer code first, without the loop variable in scope, and store its value in the alloca
        init_value = self._emit(node.init_expr)
        self.builder.store(value=init_value, ptr=var_addr)

        # Make the new basic block for the loop header, inserting it after the current block
        loop_body_bb = self.builder.function.append_basic_block("loopbody")

        # Insert an explicit fall through from the current block to loop_body_bb, then start insertion into it
        self.builder.branch(target=loop_body_bb)
        self.builder.position_at_start(block=loop_body_bb)

        # Within the loop, the variable refers to the stack slot allocated with alloca
        # NOTE if it shadows an existing variable, we have to restore it, so we save it now
        old_var_addr = self.func_symtab.get(node.id_name)
        self.func_symtab[node.id_name] = var_addr

        # Emit the body of the loop
        # NOTE this, like any other expr, can change the current BB
        _body_value = self._emit(node.body_expr)  # NOTE we ignore the computed value

        # Compute the end-loop condition and convert it
        cond_value = self.builder.fcmp_ordered(
            "!=", self._emit(node.cond_expr), FALSE, name="loopcond"
        )

        # Emit the step value (if not specified, use 1.0)
        step_value = ONE if node.step_expr is None else self._emit(node.step_expr)

        # Reload, increment, and restore the alloca
        # This handles the case where the body of the loop mutates the variable
        curr_var_value = self.builder.load(ptr=var_addr, name=node.id_name)
        next_var_value = self.builder.fadd(curr_var_value, step_value, name="nextloopvar")
        self.builder.store(value=next_var_value, ptr=var_addr)

        # Create the "after loop" block ('endfor') and insert it
        after_loop_bb = self.builder.function.append_basic_block("endfor")

        # Insert a conditional branch in the end of the loop
        self.builder.cbranch(
            cond_value, truebr=loop_body_bb, falsebr=after_loop_bb,
        )

        # Any new code will be inserted in after_loop_bb
        self.builder.position_at_start(block=after_loop_bb)

        # Remove the loop variable from the symbol table
        if old_var_addr is None:
            del self.func_symtab[node.id_name]
        else:
            self.func_symtab[node.id_name] = old_var_addr  # restore the shadowed variable

        return ZERO  # NOTE the 'for' expression always returns 0.0

    def _emit_CallExpr(self, node: kal_ast.CallExpr) -> ir.Value:
        # Look up the name in the global module table
        callee_fn = self.module.globals.get(node.callee)

        if not isinstance(callee_fn, ir.Function):
            raise GenerateCodeError(f"Call to unknown function '{node.callee}'")
        elif len(callee_fn.args) != len(node.args):
            raise GenerateCodeError(f"Call argument length mismatch for '{node.callee}'")

        return self.builder.call(
            fn=callee_fn, args=[self._emit(arg) for arg in node.args], name="calltmp"
        )

    def _emit_Prototype(self, node: kal_ast.Prototype) -> ir.Value:
        fn_name = node.name
        fn_type = ir.FunctionType(
            return_type=ir.DoubleType(), args=[ir.DoubleType() for _ in range(len(node.params))],
        )

        if (fn := self.module.globals.get(fn_name)) is None:
            # Create a new function and name its arguments
            fn = ir.Function(module=self.module, ftype=fn_type, name=fn_name)
            for arg, arg_name in zip(fn.args, node.params):
                arg.name = arg_name

        elif not isinstance(fn, ir.Function):
            raise GenerateCodeError(f"Function/global name collision '{fn_name}'")
        elif not fn.is_declaration:
            raise GenerateCodeError(f"Redefinition of '{fn_name}'")
        elif len(fn.function_type.args) != len(fn_type.args):
            raise GenerateCodeError(f"Definition of '{fn_name}' with wrong argument count")

        return fn

    def _emit_Function(self, node: kal_ast.Function) -> ir.Value:
        # Reset func_symtab and create the function skeleton from the prototype
        # NOTE prototype generation pre-populates the symbol table with arguments
        self.func_symtab = {}
        fn: ir.Function = self._emit(node.proto)

        # Create a new basic block to start insertion into
        bb_entry = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block=bb_entry)

        # Add the function arguments to the symbol table and create their allocas
        for arg in fn.args:
            arg_addr = self.__alloca(var_name=arg.name)
            self.builder.store(value=arg, ptr=arg_addr)
            assert arg.name not in self.func_symtab
            self.func_symtab[arg.name] = arg_addr

        # Finish off the function
        fn_return_value: ir.Value = self._emit(node.body)
        self.builder.ret(value=fn_return_value)

        return fn
