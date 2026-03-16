"""
Semantic analyser for MCPScript.

Responsibilities:
  1. Build a symbol table (scoped).
  2. Check that every identifier is declared before use.
  3. Type-check expressions and statements.
  4. Ensure return types match function declarations.
  5. Detect duplicate declarations in the same scope.

After a successful analysis every Expr node has its ``inferred_type``
attribute set to one of: "int", "float", "bool", "string".
"""

from __future__ import annotations

from typing import Optional

from .ast_nodes import (
    ASTVisitor, AssignStmt, BinaryExpr, Block, CallExpr, ExprStmt,
    FunctionDeclStmt, IdentifierExpr, IfStmt, LiteralExpr, Parameter,
    PrintStmt, Program, ReturnStmt, UnaryExpr, VarDeclStmt, WhileStmt,
)


class SemanticError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"SemanticError at {line}:{column} – {message}")
        self.line = line
        self.column = column


# ---------------------------------------------------------------------------
# Symbol / scope helpers
# ---------------------------------------------------------------------------

class Symbol:
    def __init__(self, name: str, sym_type: str, is_function: bool = False,
                 param_types: Optional[list[str]] = None,
                 return_type: Optional[str] = None) -> None:
        self.name = name
        self.sym_type = sym_type          # type for variables; return type for functions
        self.is_function = is_function
        self.param_types: list[str] = param_types or []
        self.return_type = return_type


class Scope:
    def __init__(self, parent: Optional["Scope"] = None) -> None:
        self._symbols: dict[str, Symbol] = {}
        self.parent = parent

    def define(self, sym: Symbol) -> None:
        if sym.name in self._symbols:
            raise KeyError(sym.name)
        self._symbols[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self._symbols:
            return self._symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


# ---------------------------------------------------------------------------
# Type compatibility rules
# ---------------------------------------------------------------------------

NUMERIC = {"int", "float"}


def _coerce(t1: str, t2: str) -> str:
    """Return the result type when combining two numeric types; raise on mismatch."""
    if t1 == t2:
        return t1
    if t1 in NUMERIC and t2 in NUMERIC:
        return "float"
    raise TypeError(f"Type mismatch: {t1!r} vs {t2!r}")


# ---------------------------------------------------------------------------
# Semantic Analyzer
# ---------------------------------------------------------------------------

class SemanticAnalyzer(ASTVisitor):
    """Walk the AST, check types and scopes, annotate expression types."""

    def __init__(self) -> None:
        self._scope: Scope = Scope()   # global scope
        self._current_return_type: Optional[str] = None
        self._errors: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, program: Program) -> list[str]:
        """Return a list of error messages (empty means success)."""
        self._errors.clear()
        self.visit_Program(program)
        return self._errors

    # ------------------------------------------------------------------
    # Error helpers
    # ------------------------------------------------------------------

    def _error(self, msg: str, line: int, col: int) -> None:
        self._errors.append(f"SemanticError at {line}:{col} – {msg}")

    # ------------------------------------------------------------------
    # Statement visitors
    # ------------------------------------------------------------------

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            stmt.accept(self)

    def visit_VarDeclStmt(self, node: VarDeclStmt) -> None:
        declared_type = node.type_annotation.name
        init_type = self._visit_expr(node.initializer)
        if init_type and init_type != declared_type:
            # Allow int → float widening
            if not (declared_type == "float" and init_type == "int"):
                self._error(
                    f"Variable '{node.name}' declared as '{declared_type}' "
                    f"but initialised with '{init_type}'",
                    node.line, node.column,
                )
        sym = Symbol(name=node.name, sym_type=declared_type)
        try:
            self._scope.define(sym)
        except KeyError:
            self._error(f"Variable '{node.name}' already declared in this scope",
                        node.line, node.column)

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        sym = self._scope.lookup(node.name)
        if sym is None:
            self._error(f"Undefined variable '{node.name}'", node.line, node.column)
            return
        if sym.is_function:
            self._error(f"Cannot assign to function '{node.name}'", node.line, node.column)
            return
        val_type = self._visit_expr(node.value)
        if val_type and val_type != sym.sym_type:
            if not (sym.sym_type == "float" and val_type == "int"):
                self._error(
                    f"Cannot assign '{val_type}' to variable '{node.name}' of type '{sym.sym_type}'",
                    node.line, node.column,
                )

    def visit_IfStmt(self, node: IfStmt) -> None:
        cond_type = self._visit_expr(node.condition)
        if cond_type and cond_type != "bool":
            self._error(f"If condition must be 'bool', got '{cond_type}'",
                        node.condition.line, node.condition.column)
        self._visit_block(node.then_branch)
        if node.else_branch:
            self._visit_block(node.else_branch)

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        cond_type = self._visit_expr(node.condition)
        if cond_type and cond_type != "bool":
            self._error(f"While condition must be 'bool', got '{cond_type}'",
                        node.condition.line, node.condition.column)
        self._visit_block(node.body)

    def visit_FunctionDeclStmt(self, node: FunctionDeclStmt) -> None:
        ret_type = node.return_type.name
        param_types = [p.type_annotation.name for p in node.parameters]
        fn_sym = Symbol(
            name=node.name,
            sym_type=ret_type,
            is_function=True,
            param_types=param_types,
            return_type=ret_type,
        )
        try:
            self._scope.define(fn_sym)
        except KeyError:
            self._error(f"Function '{node.name}' already declared in this scope",
                        node.line, node.column)

        # Analyse body in a new inner scope
        outer = self._scope
        outer_ret = self._current_return_type
        self._scope = Scope(parent=outer)
        self._current_return_type = ret_type

        for param in node.parameters:
            p_sym = Symbol(name=param.name, sym_type=param.type_annotation.name)
            try:
                self._scope.define(p_sym)
            except KeyError:
                self._error(f"Duplicate parameter '{param.name}'",
                            param.line, param.column)

        for stmt in node.body.statements:
            stmt.accept(self)

        self._scope = outer
        self._current_return_type = outer_ret

    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        if self._current_return_type is None:
            self._error("'return' outside of a function", node.line, node.column)
            return
        if node.value is None:
            if self._current_return_type != "void":
                self._error(
                    f"Function expects return type '{self._current_return_type}', "
                    "but 'return' has no value",
                    node.line, node.column,
                )
            return
        ret_type = self._visit_expr(node.value)
        expected = self._current_return_type
        if ret_type and ret_type != expected:
            if not (expected == "float" and ret_type == "int"):
                self._error(
                    f"Return type mismatch: expected '{expected}', got '{ret_type}'",
                    node.line, node.column,
                )

    def visit_PrintStmt(self, node: PrintStmt) -> None:
        for arg in node.arguments:
            self._visit_expr(arg)

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self._visit_expr(node.expression)

    def visit_Block(self, node: Block) -> None:
        for stmt in node.statements:
            stmt.accept(self)

    # ------------------------------------------------------------------
    # Expression visitors (return inferred type string or None on error)
    # ------------------------------------------------------------------

    def _visit_expr(self, expr) -> Optional[str]:
        try:
            result = expr.accept(self)
            return result
        except Exception as exc:  # noqa: BLE001
            self._error(str(exc), expr.line, expr.column)
            return None

    def visit_LiteralExpr(self, node: LiteralExpr) -> str:
        if isinstance(node.value, bool):
            t = "bool"
        elif isinstance(node.value, int):
            t = "int"
        elif isinstance(node.value, float):
            t = "float"
        elif isinstance(node.value, str):
            t = "string"
        else:
            t = "unknown"
        node.inferred_type = t
        return t

    def visit_IdentifierExpr(self, node: IdentifierExpr) -> str:
        sym = self._scope.lookup(node.name)
        if sym is None:
            self._error(f"Undefined identifier '{node.name}'", node.line, node.column)
            node.inferred_type = "unknown"
            return "unknown"
        node.inferred_type = sym.sym_type
        return sym.sym_type

    def visit_BinaryExpr(self, node: BinaryExpr) -> str:
        lt = self._visit_expr(node.left) or "unknown"
        rt = self._visit_expr(node.right) or "unknown"

        arithmetic_ops = {"+", "-", "*", "/", "%"}
        comparison_ops = {"<", "<=", ">", ">="}
        equality_ops = {"==", "!="}
        logical_ops = {"and", "or"}

        op = node.operator
        result: str

        if op in arithmetic_ops:
            if op == "+" and "string" in (lt, rt):
                if lt != rt:
                    self._error(
                        f"Operator '+' requires both operands to be 'string', got '{lt}' and '{rt}'",
                        node.line, node.column,
                    )
                result = "string"
            else:
                if lt not in NUMERIC or rt not in NUMERIC:
                    self._error(
                        f"Operator '{op}' requires numeric operands, got '{lt}' and '{rt}'",
                        node.line, node.column,
                    )
                result = "float" if "float" in (lt, rt) else "int"
        elif op in comparison_ops:
            if lt not in NUMERIC or rt not in NUMERIC:
                self._error(
                    f"Operator '{op}' requires numeric operands, got '{lt}' and '{rt}'",
                    node.line, node.column,
                )
            result = "bool"
        elif op in equality_ops:
            if lt != rt and not (lt in NUMERIC and rt in NUMERIC):
                self._error(
                    f"Equality operator '{op}' requires same types, got '{lt}' and '{rt}'",
                    node.line, node.column,
                )
            result = "bool"
        elif op in logical_ops:
            if lt != "bool" or rt != "bool":
                self._error(
                    f"Logical operator '{op}' requires 'bool' operands, got '{lt}' and '{rt}'",
                    node.line, node.column,
                )
            result = "bool"
        else:
            self._error(f"Unknown operator '{op}'", node.line, node.column)
            result = "unknown"

        node.inferred_type = result
        return result

    def visit_UnaryExpr(self, node: UnaryExpr) -> str:
        ot = self._visit_expr(node.operand) or "unknown"
        if node.operator == "-":
            if ot not in NUMERIC:
                self._error(f"Unary '-' requires numeric operand, got '{ot}'",
                            node.line, node.column)
            node.inferred_type = ot
            return ot
        if node.operator == "not":
            if ot != "bool":
                self._error(f"'not' requires 'bool' operand, got '{ot}'",
                            node.line, node.column)
            node.inferred_type = "bool"
            return "bool"
        self._error(f"Unknown unary operator '{node.operator}'", node.line, node.column)
        node.inferred_type = "unknown"
        return "unknown"

    def visit_CallExpr(self, node: CallExpr) -> str:
        sym = self._scope.lookup(node.callee)
        if sym is None:
            self._error(f"Undefined function '{node.callee}'", node.line, node.column)
            node.inferred_type = "unknown"
            return "unknown"
        if not sym.is_function:
            self._error(f"'{node.callee}' is not a function", node.line, node.column)
            node.inferred_type = "unknown"
            return "unknown"
        if len(node.arguments) != len(sym.param_types):
            self._error(
                f"Function '{node.callee}' expects {len(sym.param_types)} argument(s), "
                f"got {len(node.arguments)}",
                node.line, node.column,
            )
        for i, (arg, expected) in enumerate(zip(node.arguments, sym.param_types)):
            arg_type = self._visit_expr(arg) or "unknown"
            if arg_type != expected:
                if not (expected == "float" and arg_type == "int"):
                    self._error(
                        f"Argument {i + 1} of '{node.callee}': expected '{expected}', got '{arg_type}'",
                        arg.line, arg.column,
                    )
        ret = sym.return_type or "unknown"
        node.inferred_type = ret
        return ret

    # ------------------------------------------------------------------
    # Block helper (new scope)
    # ------------------------------------------------------------------

    def _visit_block(self, block: Block) -> None:
        outer = self._scope
        self._scope = Scope(parent=outer)
        for stmt in block.statements:
            stmt.accept(self)
        self._scope = outer
