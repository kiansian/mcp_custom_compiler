"""Unit tests for the MCPScript parser."""

import pytest

from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, ParseError
from src.compiler.ast_nodes import (
    AssignStmt, BinaryExpr, Block, CallExpr, ExprStmt, FunctionDeclStmt,
    IdentifierExpr, IfStmt, LiteralExpr, PrintStmt, Program,
    ReturnStmt, UnaryExpr, VarDeclStmt, WhileStmt,
)


def parse(source: str) -> Program:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def first_stmt(source: str):
    return parse(source).statements[0]


class TestVarDecl:
    def test_int_decl(self):
        node = first_stmt("let x: int = 42;")
        assert isinstance(node, VarDeclStmt)
        assert node.name == "x"
        assert node.type_annotation.name == "int"
        assert isinstance(node.initializer, LiteralExpr)
        assert node.initializer.value == 42

    def test_float_decl(self):
        node = first_stmt("let pi: float = 3.14;")
        assert isinstance(node, VarDeclStmt)
        assert node.type_annotation.name == "float"

    def test_string_decl(self):
        node = first_stmt('let s: string = "hello";')
        assert isinstance(node.initializer, LiteralExpr)
        assert node.initializer.value == "hello"

    def test_bool_decl(self):
        node = first_stmt("let flag: bool = true;")
        assert isinstance(node.initializer, LiteralExpr)
        assert node.initializer.value is True


class TestAssignment:
    def test_simple_assignment(self):
        prog = parse("let x: int = 0; x = 5;")
        node = prog.statements[1]
        assert isinstance(node, AssignStmt)
        assert node.name == "x"


class TestBinaryExpressions:
    def test_addition(self):
        node = first_stmt("let r: int = 1 + 2;")
        expr = node.initializer
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "+"

    def test_operator_precedence(self):
        # 1 + 2 * 3  →  1 + (2 * 3)
        node = first_stmt("let r: int = 1 + 2 * 3;")
        expr = node.initializer
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "+"
        assert isinstance(expr.right, BinaryExpr)
        assert expr.right.operator == "*"

    def test_logical_and(self):
        node = first_stmt("let r: bool = true and false;")
        expr = node.initializer
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "and"


class TestUnaryExpressions:
    def test_negation(self):
        node = first_stmt("let x: int = -5;")
        expr = node.initializer
        assert isinstance(expr, UnaryExpr)
        assert expr.operator == "-"

    def test_not(self):
        node = first_stmt("let x: bool = not true;")
        expr = node.initializer
        assert isinstance(expr, UnaryExpr)
        assert expr.operator == "not"


class TestIfStatement:
    def test_if_only(self):
        src = "if x > 0 { let y: int = 1; }"
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        assert node.else_branch is None
        assert isinstance(node.then_branch, Block)

    def test_if_else(self):
        src = "if x > 0 { let y: int = 1; } else { let y: int = 2; }"
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        assert node.else_branch is not None


class TestWhileStatement:
    def test_while(self):
        src = "while x > 0 { x = x - 1; }"
        node = first_stmt(src)
        assert isinstance(node, WhileStmt)
        assert isinstance(node.body, Block)


class TestFunctionDecl:
    def test_fn_no_params(self):
        src = "fn greet() -> string { return \"hi\"; }"
        node = first_stmt(src)
        assert isinstance(node, FunctionDeclStmt)
        assert node.name == "greet"
        assert len(node.parameters) == 0
        assert node.return_type.name == "string"

    def test_fn_with_params(self):
        src = "fn add(a: int, b: int) -> int { return a + b; }"
        node = first_stmt(src)
        assert isinstance(node, FunctionDeclStmt)
        assert len(node.parameters) == 2
        assert node.parameters[0].name == "a"
        assert node.parameters[1].type_annotation.name == "int"


class TestPrintStatement:
    def test_print_single(self):
        node = first_stmt("print(42);")
        assert isinstance(node, PrintStmt)
        assert len(node.arguments) == 1

    def test_print_multiple(self):
        node = first_stmt('print("x =", x);')
        assert isinstance(node, PrintStmt)
        assert len(node.arguments) == 2


class TestCallExpression:
    def test_call_no_args(self):
        node = first_stmt("foo();")
        assert isinstance(node, ExprStmt)
        assert isinstance(node.expression, CallExpr)
        assert node.expression.callee == "foo"

    def test_call_with_args(self):
        node = first_stmt("add(1, 2);")
        assert isinstance(node, ExprStmt)
        call = node.expression
        assert isinstance(call, CallExpr)
        assert len(call.arguments) == 2


class TestParseErrors:
    def test_missing_semicolon(self):
        with pytest.raises(ParseError):
            parse("let x: int = 5")

    def test_missing_type_annotation(self):
        with pytest.raises(ParseError):
            parse("let x = 5;")

    def test_unclosed_block(self):
        with pytest.raises(ParseError):
            parse("if true { let x: int = 1;")
