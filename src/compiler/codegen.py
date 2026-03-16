"""
Code generator for MCPScript → Python source.

The generator performs a single-pass tree-walk and emits valid Python 3
that can be executed directly (via exec() or saved as a .py file).

Type annotations are dropped in the output; all MCPScript types map to
native Python types at runtime.
"""

from __future__ import annotations

from .ast_nodes import (
    ASTVisitor, AssignStmt, BinaryExpr, Block, CallExpr, ExprStmt,
    FunctionDeclStmt, IdentifierExpr, IfStmt, LiteralExpr, PrintStmt,
    Program, ReturnStmt, UnaryExpr, VarDeclStmt, WhileStmt,
)


class CodeGenError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        super().__init__(f"CodeGenError at {line}:{column} – {message}")
        self.line = line
        self.column = column


class CodeGenerator(ASTVisitor):
    """Emit Python 3 source from an MCPScript AST."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, program: Program) -> str:
        self._lines = []
        self._indent = 0
        self.visit_Program(program)
        return "\n".join(self._lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, line: str) -> None:
        self._lines.append("    " * self._indent + line)

    def _indented(self):
        """Context manager to increase / decrease indent."""
        class _Ctx:
            def __init__(self_, /) -> None:
                pass
            def __enter__(self_, /) -> "_Ctx":
                self._indent += 1
                return self_
            def __exit__(self_, *_) -> None:
                self._indent -= 1
        return _Ctx()

    # ------------------------------------------------------------------
    # Statement visitors
    # ------------------------------------------------------------------

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            stmt.accept(self)

    def visit_VarDeclStmt(self, node: VarDeclStmt) -> None:
        init = self._expr(node.initializer)
        self._emit(f"{node.name} = {init}")

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        val = self._expr(node.value)
        self._emit(f"{node.name} = {val}")

    def visit_IfStmt(self, node: IfStmt) -> None:
        cond = self._expr(node.condition)
        self._emit(f"if {cond}:")
        with self._indented():
            self._visit_block_body(node.then_branch)
        if node.else_branch:
            self._emit("else:")
            with self._indented():
                self._visit_block_body(node.else_branch)

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        cond = self._expr(node.condition)
        self._emit(f"while {cond}:")
        with self._indented():
            self._visit_block_body(node.body)

    def visit_FunctionDeclStmt(self, node: FunctionDeclStmt) -> None:
        params = ", ".join(p.name for p in node.parameters)
        self._emit(f"def {node.name}({params}):")
        with self._indented():
            if not node.body.statements:
                self._emit("pass")
            else:
                for stmt in node.body.statements:
                    stmt.accept(self)

    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        if node.value is None:
            self._emit("return")
        else:
            self._emit(f"return {self._expr(node.value)}")

    def visit_PrintStmt(self, node: PrintStmt) -> None:
        args = ", ".join(self._expr(a) for a in node.arguments)
        self._emit(f"print({args})")

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self._emit(self._expr(node.expression))

    def visit_Block(self, node: Block) -> None:
        self._visit_block_body(node)

    def _visit_block_body(self, block: Block) -> None:
        if not block.statements:
            self._emit("pass")
        else:
            for stmt in block.statements:
                stmt.accept(self)

    # ------------------------------------------------------------------
    # Expression visitors – return a Python expression string
    # ------------------------------------------------------------------

    def _expr(self, expr) -> str:
        return expr.accept(self)

    def visit_LiteralExpr(self, node: LiteralExpr) -> str:
        if isinstance(node.value, bool):
            return "True" if node.value else "False"
        if isinstance(node.value, str):
            return repr(node.value)
        return str(node.value)

    def visit_IdentifierExpr(self, node: IdentifierExpr) -> str:
        return node.name

    def visit_BinaryExpr(self, node: BinaryExpr) -> str:
        left = self._expr(node.left)
        right = self._expr(node.right)
        op = node.operator
        # Map MCPScript operators to Python
        py_ops = {
            "and": "and",
            "or":  "or",
            "==":  "==",
            "!=":  "!=",
            "<":   "<",
            "<=":  "<=",
            ">":   ">",
            ">=":  ">=",
            "+":   "+",
            "-":   "-",
            "*":   "*",
            "/":   "/",
            "%":   "%",
        }
        py_op = py_ops.get(op)
        if py_op is None:
            raise CodeGenError(f"Unknown binary operator '{op}'")
        return f"({left} {py_op} {right})"

    def visit_UnaryExpr(self, node: UnaryExpr) -> str:
        operand = self._expr(node.operand)
        if node.operator == "-":
            return f"(-{operand})"
        if node.operator == "not":
            return f"(not {operand})"
        raise CodeGenError(f"Unknown unary operator '{node.operator}'")

    def visit_CallExpr(self, node: CallExpr) -> str:
        args = ", ".join(self._expr(a) for a in node.arguments)
        return f"{node.callee}({args})"
