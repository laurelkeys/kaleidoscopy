from typing import Any, Dict

import llvmlite.ir as ir

import kal_ast
import kal_ops


class NodeVisitor:
    """ Base class for visiting AST nodes. """

    def _visit(self, node: kal_ast.Node) -> Any:
        """ Visit a node. """
        method = f"_visit_{node.__class__.__name__}"
        visitor = getattr(self, method)
        return visitor(node)


class GenerateCodeError(Exception):
    pass


class LLVMCodeGenerator(NodeVisitor):
    """ Node visitor class that generates LLVM IR code.

        Note: each `_visit_<Node>()` method should return an appropriate `ir.Value`.
    """

    def __init__(self):
        # Top-level container of all other LLVM IR objects
        self.module: ir.Module = ir.Module()

        # Current IR builder
        self.builder: ir.IRBuilder = None

        # Manages a symbol table while a function is being visited
        self.symtab: Dict[str, ir.Value] = {}

    def generate_code(self, node: kal_ast.Node):
        assert isinstance(node, (kal_ast.Prototype, kal_ast.Function))
        return self._visit(node)

    def _visit_NumberExpr(self, node: kal_ast.NumberExpr) -> ir.Value:
        return ir.Constant(ir.DoubleType(), float(node.val))

    def _visit_VariableExpr(self, node: kal_ast.VariableExpr) -> ir.Value:
        if (value := self.symtab.get(node.name)) is not None:
            return value
        raise GenerateCodeError(f"Unknown variable name '{node.name}'")

    def _visit_BinaryExpr(self, node: kal_ast.BinaryExpr) -> ir.Value:
        lhs = self._visit(node.lhs)
        rhs = self._visit(node.rhs)

        if node.op == "+":
            return self.builder.fadd(lhs, rhs, name="addtmp")
        elif node.op == "-":
            return self.builder.fsub(lhs, rhs, name="subtmp")
        elif node.op == "*":
            return self.builder.fmul(lhs, rhs, name="multmp")
        elif node.op == "<":
            # NOTE unordered means that either operand may be a QNAN (quite NaN)
            fcmp = self.builder.fcmp_unordered(cmpop="<", lhs=lhs, rhs=rhs, name="cmptmp")
            # Convert unsigned int 0 or 1 (bool) to double 0.0 or 1.0
            return self.builder.uitofp(fcmp, ir.DoubleType(), "booltmp")
        else:
            if node.op not in kal_ops.operators:
                raise GenerateCodeError(f"Unknown binary operator '{node.op}'")
            # User-defined binary operator
            user_def_bin_op_fn = self.module.globals[f"binary{node.op}"]
            return self.builder.call(fn=user_def_bin_op_fn, args=[lhs, rhs], name="binop")

    def _visit_IfExpr(self, node: kal_ast.IfExpr) -> ir.Value:
        cond_value = self._visit(node.cond_expr)
        # NOTE ordered means that neither operand can be a QNAN (quite NaN)
        fcmp = self.builder.fcmp_ordered(
            cmpop="!=", lhs=cond_value, rhs=ir.Constant(ir.DoubleType(), 0.0), name="ifcond",
        )

        # Create basic blocks to express the control flow
        then_bb = ir.Block(self.builder.function, "then")
        else_bb = ir.Block(self.builder.function, "else")
        merge_bb = ir.Block(self.builder.function, "endif")
        self.builder.cbranch(cond=fcmp, truebr=then_bb, falsebr=else_bb)

        # Emit the 'then' block
        self.builder.function.basic_blocks.append(then_bb)
        self.builder.position_at_start(block=then_bb)
        then_value = self._visit(node.then_expr)
        self.builder.branch(target=merge_bb)  # branch to 'endif' after executing 'then'

        # NOTE Emission of then_value can modify the current basic block, so we
        # update then_bb for the PHI to remember which block the 'then' ends in
        then_bb = self.builder.block

        # Emit the 'else' block
        self.builder.function.basic_blocks.append(else_bb)
        self.builder.position_at_start(block=else_bb)
        else_value = self._visit(node.else_expr)
        self.builder.branch(target=merge_bb)  # branch to 'endif' after executing 'else'

        # NOTE Emission of else_value can modify the current basic block, so we
        # update else_bb for the PHI to remember which block the 'else' ends in
        else_bb = self.builder.block

        # Emit the merge ('endif') block
        self.builder.function.basic_blocks.append(merge_bb)
        self.builder.position_at_start(block=merge_bb)
        phi: ir.PhiInstr = self.builder.phi(typ=ir.DoubleType(), name="iftmp")
        phi.add_incoming(value=then_value, block=then_bb)
        phi.add_incoming(value=else_value, block=else_bb)
        return phi

    def _visit_ForExpr(self, node: kal_ast.ForExpr) -> ir.Value:
        # Emit the initializer code first, without the loop variable in scope
        init_value = self._visit(node.init_expr)

        # Make the new basic block for the loop header, inserting it after the current block
        preheader_bb = self.builder.block
        loop_body_bb = ir.Block(self.builder.function, "loopbody")
        self.builder.function.basic_blocks.append(loop_body_bb)

        # Insert an explicit fall through from the current block to loop_body_bb
        self.builder.branch(target=loop_body_bb)

        # Start insertion in the loop_body_bb
        self.builder.position_at_start(block=loop_body_bb)

        # Start the PHI node with an entry for init_value
        phi: ir.PhiInstr = self.builder.phi(typ=ir.DoubleType(), name=node.id_name)
        phi.add_incoming(value=init_value, block=preheader_bb)

        # Within the loop, the variable is defined equal to the PHI node
        # If it shadows an existing variable, we have to restore it, so we save it now
        old_value = self.symtab.get(node.id_name)
        self.symtab[node.id_name] = phi

        # Emit the body of the loop
        # NOTE This, like any other expr, can change the current BB
        _body_value = self._visit(node.body_expr)  # NOTE we ignore the computed value

        # Emit the step value
        step_value = (
            ir.Constant(ir.DoubleType(), 1.0)  # if not specified, use 1.0
            if node.step_expr is None
            else self._visit(node.step_expr)
        )

        next_loop_var_value = self.builder.fadd(phi, step_value, "nextloopvar")

        # Compute the end-loop condition and convert it to a bool
        cond_value = self._visit(node.cond_expr)
        fcmp = self.builder.fcmp_ordered(
            cmpop="!=", lhs=cond_value, rhs=ir.Constant(ir.DoubleType(), 0.0), name="loopcond"
        )

        # Create the "after loop" block ('endfor') and insert it
        loop_end_bb = self.builder.block
        after_loop_bb = ir.Block(self.builder.function, "endfor")
        self.builder.function.basic_blocks.append(after_loop_bb)

        # Insert the conditional branch into the end of loop_end_bb
        self.builder.cbranch(cond=fcmp, truebr=loop_body_bb, falsebr=after_loop_bb)

        # Any new code will be inserted in after_loop_bb
        self.builder.position_at_start(block=after_loop_bb)

        # Add a new entry to the PHI node for the backedge
        phi.add_incoming(value=next_loop_var_value, block=loop_end_bb)

        # Remove the loop variable from the symbol table
        if old_value is None:
            del self.symtab[node.id_name]
        else:
            self.symtab[node.id_name] = old_value  # restore the shadowed variable

        # The 'for' expression always returns 0.0
        return ir.Constant(ir.DoubleType(), 0.0)

    def _visit_CallExpr(self, node: kal_ast.CallExpr) -> ir.Value:
        # Look up the name in the global module table
        callee_fn = self.module.globals.get(node.callee, None)

        if callee_fn is None or not isinstance(callee_fn, ir.Function):
            raise GenerateCodeError(f"Call to unknown function '{node.callee}'")
        elif len(callee_fn.args) != len(node.args):
            raise GenerateCodeError(f"Call argument length mismatch for '{node.callee}'")

        call_args = [self._visit(arg) for arg in node.args]
        return self.builder.call(fn=callee_fn, args=call_args, name="calltmp")

    def _visit_Prototype(self, node: kal_ast.Prototype) -> ir.Value:
        fn_name = node.name
        fn_type = ir.FunctionType(
            return_type=ir.DoubleType(), args=[ir.DoubleType() for _ in range(len(node.params))],
        )  # NOTE Kaleidoscope uses double precision floating point for all values

        if fn_name in self.module.globals:
            fn = self.module.globals[fn_name]
            if not isinstance(fn, ir.Function):
                raise GenerateCodeError(f"Function/global name collision '{fn_name}'")
            elif not fn.is_declaration:
                raise GenerateCodeError(f"Redefinition of '{fn_name}'")
            elif len(fn.function_type.args) != len(fn_type.args):
                raise GenerateCodeError(f"Definition of '{fn_name}' with wrong argument count")
        else:
            # Create a new function and set its arguments names
            fn = ir.Function(module=self.module, ftype=fn_type, name=fn_name)
            for arg, arg_name in zip(fn.args, node.params):
                arg.name = arg_name
                self.symtab[arg.name] = arg

        return fn

    def _visit_Function(self, node: kal_ast.Function) -> ir.Value:
        # NOTE prototype generation will pre-populate symtab with function arguments
        self.symtab = {}

        fn: ir.Function = self._visit(node.proto)

        # Create a new basic block to start insertion into
        bb_entry = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block=bb_entry)

        # Finish off the function
        fn_return_value: ir.Value = self._visit(node.body)
        self.builder.ret(value=fn_return_value)

        return fn
