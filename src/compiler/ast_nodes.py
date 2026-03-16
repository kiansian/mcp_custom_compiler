"""
AST node definitions for MCPScript.

Every node is a frozen dataclass.  The hierarchy mirrors the grammar:

    Program
      └─ Statement*
            ├─ VarDeclStmt
            ├─ AssignStmt
            ├─ IfStmt
            ├─ WhileStmt
            ├─ FunctionDeclStmt
            ├─ ReturnStmt
            ├─ PrintStmt
            └─ ExprStmt
    Expression
            ├─ BinaryExpr
            ├─ UnaryExpr
            ├─ LiteralExpr
            ├─ IdentifierExpr
            └─ CallExpr
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """Root of the AST hierarchy."""
    line: int = field(default=0, compare=False, kw_only=True)
    column: int = field(default=0, compare=False, kw_only=True)

    def accept(self, visitor: "ASTVisitor"):
        method = f"visit_{type(self).__name__}"
        return getattr(visitor, method)(self)


@dataclass
class Stmt(Node):
    """Base for all statement nodes."""


@dataclass
class Expr(Node):
    """Base for all expression nodes."""
    inferred_type: Optional[str] = field(default=None, init=False, compare=False)


# ---------------------------------------------------------------------------
# Type annotation  (used in declarations / function signatures)
# ---------------------------------------------------------------------------

@dataclass
class TypeAnnotation(Node):
    name: str  # "int", "float", "bool", "string"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class LiteralExpr(Expr):
    value: int | float | bool | str | None


@dataclass
class IdentifierExpr(Expr):
    name: str


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: str   # "+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or"
    right: Expr


@dataclass
class UnaryExpr(Expr):
    operator: str   # "-", "not"
    operand: Expr


@dataclass
class CallExpr(Expr):
    callee: str
    arguments: list[Expr] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class VarDeclStmt(Stmt):
    name: str
    type_annotation: TypeAnnotation
    initializer: Expr


@dataclass
class AssignStmt(Stmt):
    name: str
    value: Expr


@dataclass
class Block(Node):
    statements: list[Stmt] = field(default_factory=list)


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Block
    else_branch: Optional[Block] = None


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Block


@dataclass
class Parameter(Node):
    name: str
    type_annotation: TypeAnnotation


@dataclass
class FunctionDeclStmt(Stmt):
    name: str
    parameters: list[Parameter]
    return_type: TypeAnnotation
    body: Block


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr] = None


@dataclass
class PrintStmt(Stmt):
    arguments: list[Expr] = field(default_factory=list)


@dataclass
class ExprStmt(Stmt):
    expression: Expr


# ---------------------------------------------------------------------------
# Top-level program
# ---------------------------------------------------------------------------

@dataclass
class Program(Node):
    statements: list[Stmt] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Visitor interface (optional – used by codegen / semantic passes)
# ---------------------------------------------------------------------------

class ASTVisitor:
    """Base visitor; override the visit_* methods you care about."""

    def visit_Program(self, node: Program):
        for stmt in node.statements:
            stmt.accept(self)

    def visit_VarDeclStmt(self, node: VarDeclStmt): ...
    def visit_AssignStmt(self, node: AssignStmt): ...
    def visit_IfStmt(self, node: IfStmt): ...
    def visit_WhileStmt(self, node: WhileStmt): ...
    def visit_FunctionDeclStmt(self, node: FunctionDeclStmt): ...
    def visit_ReturnStmt(self, node: ReturnStmt): ...
    def visit_PrintStmt(self, node: PrintStmt): ...
    def visit_ExprStmt(self, node: ExprStmt): ...
    def visit_BinaryExpr(self, node: BinaryExpr): ...
    def visit_UnaryExpr(self, node: UnaryExpr): ...
    def visit_LiteralExpr(self, node: LiteralExpr): ...
    def visit_IdentifierExpr(self, node: IdentifierExpr): ...
    def visit_CallExpr(self, node: CallExpr): ...
    def visit_Block(self, node: Block):
        for stmt in node.statements:
            stmt.accept(self)
