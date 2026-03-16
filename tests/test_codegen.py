"""Unit tests for the MCPScript code generator."""

import pytest

from src.compiler.lexer import Lexer
from src.compiler.parser import Parser
from src.compiler.codegen import CodeGenerator
from src.compiler.semantic import SemanticAnalyzer


def generate(source: str) -> str:
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    errors = SemanticAnalyzer().analyze(ast)
    assert not errors, f"Semantic errors: {errors}"
    return CodeGenerator().generate(ast)


def run_generated(source: str) -> dict:
    code = generate(source)
    ns: dict = {}
    exec(code, ns)  # noqa: S102
    return ns


class TestVariableGeneration:
    def test_int_var(self):
        ns = run_generated("let x: int = 5;")
        assert ns["x"] == 5

    def test_float_var(self):
        ns = run_generated("let pi: float = 3.14;")
        assert pytest.approx(ns["pi"]) == 3.14

    def test_string_var(self):
        ns = run_generated('let s: string = "hello";')
        assert ns["s"] == "hello"

    def test_bool_var_true(self):
        ns = run_generated("let flag: bool = true;")
        assert ns["flag"] is True

    def test_bool_var_false(self):
        ns = run_generated("let flag: bool = false;")
        assert ns["flag"] is False


class TestArithmeticGeneration:
    def test_addition(self):
        ns = run_generated("let r: int = 1 + 2;")
        assert ns["r"] == 3

    def test_subtraction(self):
        ns = run_generated("let r: int = 10 - 4;")
        assert ns["r"] == 6

    def test_multiplication(self):
        ns = run_generated("let r: int = 3 * 4;")
        assert ns["r"] == 12

    def test_integer_division(self):
        ns = run_generated("let r: float = 7 / 2;")
        assert pytest.approx(ns["r"]) == 3.5

    def test_modulo(self):
        ns = run_generated("let r: int = 10 % 3;")
        assert ns["r"] == 1

    def test_precedence(self):
        ns = run_generated("let r: int = 2 + 3 * 4;")
        assert ns["r"] == 14

    def test_parentheses(self):
        ns = run_generated("let r: int = (2 + 3) * 4;")
        assert ns["r"] == 20

    def test_unary_minus(self):
        ns = run_generated("let r: int = -5;")
        assert ns["r"] == -5


class TestComparisonGeneration:
    def test_less_than(self):
        ns = run_generated("let b: bool = 1 < 2;")
        assert ns["b"] is True

    def test_equality(self):
        ns = run_generated("let b: bool = 3 == 3;")
        assert ns["b"] is True

    def test_not_equal(self):
        ns = run_generated("let b: bool = 3 != 4;")
        assert ns["b"] is True


class TestLogicalGeneration:
    def test_and(self):
        ns = run_generated("let b: bool = true and false;")
        assert ns["b"] is False

    def test_or(self):
        ns = run_generated("let b: bool = false or true;")
        assert ns["b"] is True

    def test_not(self):
        ns = run_generated("let b: bool = not true;")
        assert ns["b"] is False


class TestControlFlowGeneration:
    def test_if_true_branch(self):
        src = """
        let x: int = 0;
        if true {
            x = 10;
        }
        """
        ns = run_generated(src)
        assert ns["x"] == 10

    def test_if_false_branch(self):
        src = """
        let x: int = 0;
        if false {
            x = 10;
        } else {
            x = 20;
        }
        """
        ns = run_generated(src)
        assert ns["x"] == 20

    def test_while_loop(self):
        src = """
        let n: int = 5;
        let acc: int = 0;
        while n > 0 {
            acc = acc + n;
            n = n - 1;
        }
        """
        ns = run_generated(src)
        assert ns["acc"] == 15
        assert ns["n"] == 0


class TestFunctionGeneration:
    def test_simple_function(self):
        src = """
        fn double(x: int) -> int {
            return x * 2;
        }
        let r: int = double(7);
        """
        ns = run_generated(src)
        assert ns["r"] == 14

    def test_recursive_function(self):
        src = """
        fn fact(n: int) -> int {
            if n <= 1 {
                return 1;
            }
            return n * fact(n - 1);
        }
        let r: int = fact(5);
        """
        ns = run_generated(src)
        assert ns["r"] == 120

    def test_string_function(self):
        src = """
        fn greet(name: string) -> string {
            return "Hello, " + name;
        }
        let msg: string = greet("world");
        """
        ns = run_generated(src)
        assert ns["msg"] == "Hello, world"


class TestGeneratedCodeFormat:
    def test_function_def_present(self):
        code = generate("fn add(a: int, b: int) -> int { return a + b; }")
        assert "def add(a, b):" in code
        assert "return" in code

    def test_if_else_format(self):
        code = generate("if true { let x: int = 1; } else { let x: int = 2; }")
        assert "if True:" in code
        assert "else:" in code

    def test_while_format(self):
        code = generate("let x: int = 1; while x > 0 { x = x - 1; }")
        assert "while" in code
