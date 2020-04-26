from typing import Any, Dict

import llvmlite.ir as ir
import llvmlite.binding as llvm

import kal_ast


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
    """ Node visitor class that generates SSA values for LLVM.

        Note: each `_visit_<Node>()` method should return an appropriate `llvm.ir.Value`.
    """

    def __init__(self):
        # Top level container of all other LLVM IR objects
        self.module: ir.Module = ir.Module()

        # Current IR builder
        self.builder: ir.IRBuilder = None

        # Manages a symbol table while a function is being visited
        self.symtab: Dict[str, ir.Value] = {}

    def generate_code(self, node: kal_ast.Node):
        assert isinstance(node, (kal_ast.Prototype, kal_ast.Function))
        return self._visit(node)

    def _visit_NumberExpr(self, node: kal_ast.NumberExpr) -> ir.Value:
        return ir.Constant(ir.DoubleType, float(node.val))

    def _visit_VariableExpr(self, node: kal_ast.VariableExpr) -> ir.Value:
        if value := self.symtab[node.name]:
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
            # NOTE: unordered means that either operand may be a QNAN (quite NaN)
            fcmp = self.builder.fcmp_unordered(cmpop="<", lhs=lhs, rhs=rhs, name="cmptmp")
            # Convert unsigned int 0 or 1 (bool) to double 0.0 or 1.0
            return self.builder.uitofp(value=fcmp, typ=ir.DoubleType(), name="booltmp")
        else:
            raise GenerateCodeError(f"Unknown binary operator '{node.op}'")

    def _visit_CallExpr(self, node: kal_ast.CallExpr) -> ir.Value:
        # Look up the name in the global module table
        callee_fn = self.module.globals.get(node.callee, None)

        if callee_fn is None or not isinstance(callee_fn, ir.Function):
            raise GenerateCodeError(f"Call to unknown function '{node.callee}'")
        if len(callee_fn.args) != len(node.args):
            raise GenerateCodeError(f"Call argument length mismatch for '{node.callee}'")

        call_args = [self._visit(arg) for arg in node.args]
        return self.builder.call(fn=callee_fn, args=call_args, name="calltmp")

    def _visit_Prototype(self, node: kal_ast.Prototype) -> ir.Value:
        pass

    def _visit_Function(self, node: kal_ast.Function) -> ir.Value:
        pass
