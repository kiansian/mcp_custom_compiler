"""
Main compiler orchestrator for MCPScript.

Provides a single ``Compiler`` class that chains:
  Lexer → Parser → SemanticAnalyzer → CodeGenerator

and returns a ``CompilationResult`` with all intermediate artefacts
and any diagnostics collected.
"""

from __future__ import annotations

import io
import contextlib
from dataclasses import dataclass, field
from typing import Optional

from .lexer import Lexer, LexerError, Token
from .parser import Parser, ParseError
from .semantic import SemanticAnalyzer
from .codegen import CodeGenerator
from .ast_nodes import Program


@dataclass
class CompilationResult:
    """Encapsulates every artefact produced during compilation."""

    source: str
    tokens: list[Token] = field(default_factory=list)
    ast: Optional[Program] = None
    semantic_errors: list[str] = field(default_factory=list)
    generated_code: Optional[str] = None

    # Execution results (populated by Compiler.compile_and_run)
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_error: Optional[str] = None

    # Phase reached before the first hard error
    phase: str = "none"

    @property
    def success(self) -> bool:
        return (
            self.phase in ("codegen", "executed")
            and not self.semantic_errors
            and self.execution_error is None
        )

    def summary(self) -> str:
        lines: list[str] = [f"Phase reached: {self.phase}"]
        lines.append(f"Tokens produced: {len(self.tokens)}")
        if self.semantic_errors:
            lines.append("Semantic errors:")
            for e in self.semantic_errors:
                lines.append(f"  {e}")
        if self.generated_code is not None:
            lines.append("Generated Python code:")
            for ln in self.generated_code.splitlines():
                lines.append(f"  {ln}")
        if self.stdout:
            lines.append("Program output:")
            for ln in self.stdout.splitlines():
                lines.append(f"  {ln}")
        if self.stderr:
            lines.append("Program stderr:")
            for ln in self.stderr.splitlines():
                lines.append(f"  {ln}")
        if self.execution_error:
            lines.append(f"Execution error: {self.execution_error}")
        return "\n".join(lines)


class Compiler:
    """
    Multi-phase MCPScript compiler.

    Usage::

        result = Compiler().compile("let x: int = 1 + 2;")
        result = Compiler().compile_and_run("print(1 + 2);")
    """

    def compile(self, source: str) -> CompilationResult:
        """
        Run all compilation phases up to (and including) code generation.
        Returns a CompilationResult; never raises – errors are captured.
        """
        result = CompilationResult(source=source)

        # ── Phase 1: Lexing ─────────────────────────────────────────────
        try:
            lexer = Lexer(source)
            result.tokens = lexer.tokenize()
            result.phase = "lex"
        except LexerError as exc:
            result.semantic_errors.append(str(exc))
            result.phase = "lex_error"
            return result

        # ── Phase 2: Parsing ─────────────────────────────────────────────
        try:
            parser = Parser(result.tokens)
            result.ast = parser.parse()
            result.phase = "parse"
        except ParseError as exc:
            result.semantic_errors.append(str(exc))
            result.phase = "parse_error"
            return result

        # ── Phase 3: Semantic analysis ────────────────────────────────────
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(result.ast)
        result.semantic_errors = errors
        if errors:
            result.phase = "semantic_error"
            return result
        result.phase = "semantic"

        # ── Phase 4: Code generation ──────────────────────────────────────
        try:
            gen = CodeGenerator()
            result.generated_code = gen.generate(result.ast)
            result.phase = "codegen"
        except Exception as exc:  # noqa: BLE001
            result.semantic_errors.append(f"CodeGenError: {exc}")
            result.phase = "codegen_error"

        return result

    def compile_and_run(self, source: str) -> CompilationResult:
        """
        Compile the source and execute the generated Python code.
        Captured stdout / stderr are stored on the result.
        """
        result = self.compile(source)
        if result.phase != "codegen" or result.generated_code is None:
            return result

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_buf), \
                 contextlib.redirect_stderr(stderr_buf):
                exec(result.generated_code, {})  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            result.execution_error = f"{type(exc).__name__}: {exc}"
        finally:
            result.stdout = stdout_buf.getvalue()
            result.stderr = stderr_buf.getvalue()

        if result.execution_error is None:
            result.phase = "executed"

        return result
