"""Unit tests for the MCPScript semantic analyser."""

import pytest

from src.compiler.lexer import Lexer
from src.compiler.parser import Parser
from src.compiler.semantic import SemanticAnalyzer


def check(source: str) -> list[str]:
    """Return semantic error messages for *source*."""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    return SemanticAnalyzer().analyze(ast)


def assert_ok(source: str) -> None:
    errors = check(source)
    assert errors == [], f"Expected no errors but got: {errors}"


def assert_errors(source: str, *fragments: str) -> None:
    errors = check(source)
    assert errors, f"Expected errors but found none for:\n{source}"
    joined = "\n".join(errors)
    for fragment in fragments:
        assert fragment in joined, (
            f"Expected fragment {fragment!r} in errors:\n{joined}"
        )


class TestValidPrograms:
    def test_simple_int_decl(self):
        assert_ok("let x: int = 5;")

    def test_float_decl(self):
        assert_ok("let pi: float = 3.14;")

    def test_int_assigned_to_float(self):
        assert_ok("let x: float = 1;")  # widening allowed

    def test_string_decl(self):
        assert_ok('let s: string = "hello";')

    def test_bool_decl(self):
        assert_ok("let flag: bool = true;")

    def test_arithmetic(self):
        assert_ok("let x: int = 1 + 2 * 3;")

    def test_float_arithmetic(self):
        assert_ok("let r: float = 1.0 + 2.0;")

    def test_comparison(self):
        assert_ok("let b: bool = 1 < 2;")

    def test_logical(self):
        assert_ok("let b: bool = true and false;")

    def test_string_concat(self):
        assert_ok('let s: string = "hello" + " world";')

    def test_function_decl_and_call(self):
        src = """
        fn add(a: int, b: int) -> int {
            return a + b;
        }
        let result: int = add(1, 2);
        """
        assert_ok(src)

    def test_if_statement(self):
        assert_ok("if true { let x: int = 1; }")

    def test_while_statement(self):
        assert_ok("let x: int = 5; while x > 0 { x = x - 1; }")

    def test_nested_function(self):
        src = """
        fn square(n: int) -> int {
            return n * n;
        }
        fn sum_of_squares(a: int, b: int) -> int {
            return square(a) + square(b);
        }
        """
        assert_ok(src)

    def test_print_statement(self):
        assert_ok('print("hello");')


class TestTypeErrors:
    def test_type_mismatch_decl(self):
        assert_errors('let x: int = "hello";', "int", "string")

    def test_type_mismatch_assign(self):
        src = 'let x: int = 5; x = "hello";'
        assert_errors(src, "int", "string")

    def test_non_bool_if_condition(self):
        assert_errors("if 1 { let x: int = 1; }", "bool")

    def test_non_bool_while_condition(self):
        assert_errors("while 1 { let x: int = 1; }", "bool")

    def test_wrong_operand_type_arithmetic(self):
        assert_errors('let x: int = "a" + 1;', "string")

    def test_logical_op_on_ints(self):
        assert_errors("let b: bool = 1 and 2;", "bool")

    def test_return_type_mismatch(self):
        src = 'fn foo() -> int { return "hello"; }'
        assert_errors(src, "int", "string")

    def test_wrong_arg_type(self):
        src = """
        fn greet(name: string) -> string {
            return name;
        }
        let r: string = greet(42);
        """
        assert_errors(src, "string", "int")

    def test_wrong_number_of_args(self):
        src = """
        fn add(a: int, b: int) -> int { return a + b; }
        let r: int = add(1);
        """
        assert_errors(src, "2", "1")


class TestScopeErrors:
    def test_undeclared_variable(self):
        assert_errors("let x: int = y;", "y")

    def test_duplicate_variable(self):
        assert_errors("let x: int = 1; let x: int = 2;", "already declared")

    def test_undefined_function(self):
        assert_errors("let x: int = foo(1);", "foo")

    def test_call_non_function(self):
        assert_errors("let foo: int = 5; let r: int = foo(1);", "not a function")

    def test_return_outside_function(self):
        assert_errors("return 1;", "outside")

    def test_variable_not_visible_outside_block(self):
        src = """
        if true {
            let inner: int = 10;
        }
        let x: int = inner;
        """
        assert_errors(src, "inner")
