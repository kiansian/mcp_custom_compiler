"""Integration tests for the end-to-end Compiler class."""

import pytest

from src.compiler.compiler import Compiler, CompilationResult


@pytest.fixture
def compiler():
    return Compiler()


class TestCompilePhases:
    def test_successful_compile(self, compiler: Compiler):
        result = compiler.compile("let x: int = 5;")
        assert result.phase == "codegen"
        assert result.success
        assert result.generated_code is not None

    def test_lex_error_captured(self, compiler: Compiler):
        result = compiler.compile('"unterminated')
        assert result.phase == "lex_error"
        assert not result.success
        assert result.semantic_errors

    def test_parse_error_captured(self, compiler: Compiler):
        result = compiler.compile("let x: int = 5")   # missing ;
        assert result.phase == "parse_error"
        assert not result.success

    def test_semantic_error_captured(self, compiler: Compiler):
        result = compiler.compile('let x: int = "hello";')
        assert result.phase == "semantic_error"
        assert not result.success
        assert result.semantic_errors

    def test_tokens_populated(self, compiler: Compiler):
        result = compiler.compile("let x: int = 1;")
        assert len(result.tokens) > 0

    def test_ast_populated(self, compiler: Compiler):
        result = compiler.compile("let x: int = 1;")
        assert result.ast is not None


class TestCompileAndRun:
    def test_print_output(self, compiler: Compiler):
        result = compiler.compile_and_run('print("hello");')
        assert result.stdout is not None
        assert result.stdout.strip() == "hello"

    def test_arithmetic_output(self, compiler: Compiler):
        result = compiler.compile_and_run("print(1 + 2);")
        assert result.stdout is not None
        assert "3" in result.stdout

    def test_function_and_print(self, compiler: Compiler):
        src = """
        fn add(a: int, b: int) -> int {
            return a + b;
        }
        print(add(3, 4));
        """
        result = compiler.compile_and_run(src)
        assert "7" in result.stdout

    def test_while_loop_output(self, compiler: Compiler):
        src = """
        let n: int = 3;
        while n > 0 {
            print(n);
            n = n - 1;
        }
        """
        result = compiler.compile_and_run(src)
        assert "3" in result.stdout
        assert "2" in result.stdout
        assert "1" in result.stdout

    def test_run_does_not_execute_on_errors(self, compiler: Compiler):
        result = compiler.compile_and_run('let x: int = "oops";')
        assert result.stdout is None
        assert not result.success

    def test_summary_method(self, compiler: Compiler):
        result = compiler.compile("let x: int = 42;")
        summary = result.summary()
        assert "codegen" in summary
        assert "Tokens" in summary


class TestComprehensivePrograms:
    def test_fibonacci(self, compiler: Compiler):
        src = """
        fn fib(n: int) -> int {
            if n <= 1 {
                return n;
            }
            return fib(n - 1) + fib(n - 2);
        }
        print(fib(10));
        """
        result = compiler.compile_and_run(src)
        assert result.success
        assert "55" in result.stdout

    def test_sum_1_to_100(self, compiler: Compiler):
        src = """
        let i: int = 1;
        let total: int = 0;
        while i <= 100 {
            total = total + i;
            i = i + 1;
        }
        print(total);
        """
        result = compiler.compile_and_run(src)
        assert result.success
        assert "5050" in result.stdout

    def test_string_operations(self, compiler: Compiler):
        src = """
        let first: string = "Hello";
        let second: string = ", World!";
        let msg: string = first + second;
        print(msg);
        """
        result = compiler.compile_and_run(src)
        assert result.success
        assert "Hello, World!" in result.stdout

    def test_nested_if_else(self, compiler: Compiler):
        src = """
        fn classify(n: int) -> string {
            if n < 0 {
                return "negative";
            } else {
                if n == 0 {
                    return "zero";
                } else {
                    return "positive";
                }
            }
        }
        print(classify(-5));
        print(classify(0));
        print(classify(7));
        """
        result = compiler.compile_and_run(src)
        assert result.success
        assert "negative" in result.stdout
        assert "zero" in result.stdout
        assert "positive" in result.stdout

    def test_comment_ignored(self, compiler: Compiler):
        src = """
        // This is a comment
        let x: int = 5; // inline comment
        print(x);
        """
        result = compiler.compile_and_run(src)
        assert result.success
        assert "5" in result.stdout
