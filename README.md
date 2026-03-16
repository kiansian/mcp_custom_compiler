# mcp_custom_compiler
SPE ISCP CKT team, first repo on MCP for calling custom compiler

---

## Overview

This repository implements a **comprehensive custom compiler** for a simple statically-typed scripting language called **MCPScript**, exposed as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server.

The compiler implements a full pipeline:

```
Source code
    │
    ▼
┌─────────┐   tokens   ┌──────────┐   AST   ┌──────────────────┐   AST   ┌──────────────┐   Python source
│  Lexer  │ ─────────► │  Parser  │ ──────► │ Semantic Analyser│ ──────► │ Code Generator│ ─────────────► output
└─────────┘            └──────────┘         └──────────────────┘         └──────────────┘
```

### Compiler phases

| Phase | Module | Responsibility |
|-------|--------|----------------|
| Lexing | `src/compiler/lexer.py` | Converts source text to tokens |
| Parsing | `src/compiler/parser.py` | Builds an AST via recursive descent |
| Semantic analysis | `src/compiler/semantic.py` | Type-checks, resolves identifiers, validates scopes |
| Code generation | `src/compiler/codegen.py` | Emits Python 3 source code |
| Orchestrator | `src/compiler/compiler.py` | Chains all phases; captures diagnostics |
| MCP server | `src/server.py` | Exposes compiler tools over MCP |

---

## MCPScript language

### Types

| Type | Description | Example |
|------|-------------|---------|
| `int` | 64-bit integer | `42` |
| `float` | 64-bit float | `3.14` |
| `bool` | Boolean | `true` / `false` |
| `string` | UTF-8 string | `"hello"` |

### Syntax overview

```mcpscript
// Variable declaration
let x: int = 5;
let pi: float = 3.14159;
let greeting: string = "Hello";
let flag: bool = true;

// Assignment
x = x + 1;

// Arithmetic: + - * / %
let result: int = (x + 3) * 2;

// Comparison: == != < <= > >=
let big: bool = x > 10;

// Logical: and or not
let ok: bool = flag and not big;

// String concatenation
let msg: string = "Hello" + ", World!";

// If / else
if x > 0 {
    print("positive");
} else {
    print("non-positive");
}

// While loop
while x > 0 {
    x = x - 1;
}

// Function declaration
fn add(a: int, b: int) -> int {
    return a + b;
}

// Function call
let sum: int = add(3, 4);

// Print (built-in)
print("sum =", sum);
```

---

## MCP server tools

The MCP server exposes six tools:

| Tool | Description |
|------|-------------|
| `tokenize` | Lex source code and return the token list |
| `parse` | Lex + parse and return a text representation of the AST |
| `check` | Run semantic analysis and report any errors |
| `compile` | Run all phases and return the generated Python 3 code |
| `run` | Compile and execute; return program output |
| `help` | Print the MCPScript language reference guide |

---

## Setup

### Requirements

- Python ≥ 3.10

### Installation

```bash
pip install -e ".[dev]"
```

### Running the MCP server

```bash
python -m src.server
```

Or via the installed script:

```bash
mcp-compiler
```

---

## Testing

```bash
pytest tests/ -v
```

All 138 tests cover:

- **`test_lexer.py`** – tokenisation, keywords, operators, error cases
- **`test_parser.py`** – every grammar construct, error recovery
- **`test_semantic.py`** – valid programs, type errors, scope errors
- **`test_codegen.py`** – correct Python output for every language feature
- **`test_compiler.py`** – end-to-end compilation and execution, including complex programs (Fibonacci, sum 1–100, nested functions)
