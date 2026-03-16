"""
MCP server exposing MCPScript compiler tools.

Tools provided:
  • tokenize   – lex source into tokens
  • parse      – lex + parse, return AST description
  • check      – full semantic analysis, return any errors
  • compile    – full compilation pipeline, return generated Python
  • run        – compile and execute, return program output
  • help       – describe the MCPScript language
"""

from __future__ import annotations

import json
import sys

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from src.compiler.compiler import Compiler
from src.compiler.lexer import Lexer, LexerError
from src.compiler.parser import Parser, ParseError
from src.compiler.semantic import SemanticAnalyzer

app = Server("mcp-custom-compiler")
_compiler = Compiler()


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="tokenize",
            description=(
                "Lex MCPScript source code and return the list of tokens. "
                "Useful for inspecting how the lexer breaks up input."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "MCPScript source code to tokenize.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="parse",
            description=(
                "Lex and parse MCPScript source code. Returns a compact "
                "representation of the Abstract Syntax Tree (AST)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "MCPScript source code to parse.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="check",
            description=(
                "Run the full semantic analysis pass on MCPScript source. "
                "Returns a list of type errors and undeclared-variable errors, "
                "or confirms that the code is semantically valid."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "MCPScript source code to analyse.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="compile",
            description=(
                "Compile MCPScript source code through all phases "
                "(lex → parse → semantic check → code-gen) and return "
                "the generated Python 3 source code."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "MCPScript source code to compile.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="run",
            description=(
                "Compile MCPScript source code and execute it. "
                "Returns the program's stdout output and any runtime errors."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "MCPScript source code to compile and run.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="help",
            description="Return a reference guide for the MCPScript language.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:

    if name == "tokenize":
        return _handle_tokenize(arguments.get("source", ""))

    if name == "parse":
        return _handle_parse(arguments.get("source", ""))

    if name == "check":
        return _handle_check(arguments.get("source", ""))

    if name == "compile":
        return _handle_compile(arguments.get("source", ""))

    if name == "run":
        return _handle_run(arguments.get("source", ""))

    if name == "help":
        return _handle_help()

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _handle_tokenize(source: str) -> list[types.TextContent]:
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
    except LexerError as exc:
        return [types.TextContent(type="text", text=f"Lex error: {exc}")]

    rows = [
        {"type": t.type.name, "value": t.value, "line": t.line, "col": t.column}
        for t in tokens
    ]
    output = json.dumps(rows, indent=2)
    return [types.TextContent(type="text", text=output)]


def _handle_parse(source: str) -> list[types.TextContent]:
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
    except (LexerError, ParseError) as exc:
        return [types.TextContent(type="text", text=f"Error: {exc}")]

    return [types.TextContent(type="text", text=_ast_to_text(ast))]


def _handle_check(source: str) -> list[types.TextContent]:
    result = _compiler.compile(source)
    if result.phase in ("lex_error", "parse_error"):
        errors = "\n".join(result.semantic_errors)
        return [types.TextContent(type="text", text=f"Compilation error:\n{errors}")]
    if result.semantic_errors:
        errors = "\n".join(result.semantic_errors)
        return [types.TextContent(type="text", text=f"Semantic errors found:\n{errors}")]
    return [types.TextContent(type="text", text="No errors found. Code is semantically valid.")]


def _handle_compile(source: str) -> list[types.TextContent]:
    result = _compiler.compile(source)
    if not result.success and result.generated_code is None:
        errors = "\n".join(result.semantic_errors)
        return [types.TextContent(type="text",
                                  text=f"Compilation failed (phase={result.phase}):\n{errors}")]
    if result.semantic_errors:
        errors = "\n".join(result.semantic_errors)
        return [types.TextContent(type="text",
                                  text=f"Compilation warnings:\n{errors}\n\n"
                                       f"Generated code:\n{result.generated_code}")]
    return [types.TextContent(type="text",
                              text=f"Generated Python code:\n\n{result.generated_code}")]


def _handle_run(source: str) -> list[types.TextContent]:
    result = _compiler.compile_and_run(source)
    parts: list[str] = []

    if result.semantic_errors:
        parts.append("Errors:\n" + "\n".join(result.semantic_errors))

    if result.stdout:
        parts.append("Output:\n" + result.stdout.rstrip())

    if result.stderr:
        parts.append("Stderr:\n" + result.stderr.rstrip())

    if result.execution_error:
        parts.append(f"Runtime error: {result.execution_error}")

    if not parts:
        parts.append("(no output)")

    return [types.TextContent(type="text", text="\n\n".join(parts))]


def _handle_help() -> list[types.TextContent]:
    guide = """\
MCPScript Language Reference
=============================

Types
-----
  int     – 64-bit integer          e.g. 42
  float   – 64-bit float            e.g. 3.14
  bool    – boolean                 e.g. true / false
  string  – UTF-8 string            e.g. "hello"

Variable declarations
---------------------
  let <name>: <type> = <expr>;

  Examples:
    let x: int = 5;
    let pi: float = 3.14159;
    let greeting: string = "Hello";
    let flag: bool = true;

Assignment
----------
  <name> = <expr>;

Arithmetic operators
--------------------
  +  -  *  /  %

Comparison operators
--------------------
  ==  !=  <  <=  >  >=

Logical operators
-----------------
  and  or  not

Control flow
------------
  if <condition> {
      <statements>
  } else {
      <statements>
  }

  while <condition> {
      <statements>
  }

Functions
---------
  fn <name>(<params>) -> <return_type> {
      <statements>
      return <expr>;
  }

  Example:
    fn add(a: int, b: int) -> int {
        return a + b;
    }

Built-in statements
-------------------
  print(<expr>, ...);

Comments
--------
  // single-line comment

Complete example
----------------
  let n: int = 10;
  let sum: int = 0;
  while n > 0 {
      sum = sum + n;
      n = n - 1;
  }
  print("Sum:", sum);
"""
    return [types.TextContent(type="text", text=guide)]


# ---------------------------------------------------------------------------
# AST pretty-printer (simple recursive repr)
# ---------------------------------------------------------------------------

def _ast_to_text(node, indent: int = 0) -> str:
    prefix = "  " * indent
    name = type(node).__name__

    # Leaf nodes
    if hasattr(node, "value") and not hasattr(node, "statements") \
            and not hasattr(node, "left") and not hasattr(node, "arguments") \
            and not hasattr(node, "condition"):
        return f"{prefix}{name}({node.value!r})"

    lines = [f"{prefix}{name}"]
    for attr_name, attr_val in vars(node).items():
        if attr_name in ("line", "column", "inferred_type"):
            continue
        if isinstance(attr_val, list):
            if attr_val:
                lines.append(f"{prefix}  {attr_name}:")
                for item in attr_val:
                    if hasattr(item, "__dataclass_fields__"):
                        lines.append(_ast_to_text(item, indent + 2))
                    else:
                        lines.append(f"{prefix}    {item!r}")
        elif hasattr(attr_val, "__dataclass_fields__"):
            lines.append(f"{prefix}  {attr_name}:")
            lines.append(_ast_to_text(attr_val, indent + 2))
        elif attr_val is not None:
            lines.append(f"{prefix}  {attr_name}: {attr_val!r}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _serve() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def main() -> None:
    import asyncio
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
