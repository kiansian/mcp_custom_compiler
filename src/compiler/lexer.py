"""
Lexer / Tokenizer for MCPScript.

MCPScript is a simple statically-typed scripting language with:
  - Primitive types: int, float, bool, string
  - Variable declarations:  let x: int = 5;
  - Arithmetic / comparison / logical operators
  - Control flow:  if / else, while
  - Functions:  fn add(a: int, b: int) -> int { ... }
  - Return statements, print built-in
  - Single-line comments starting with //
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


# ---------------------------------------------------------------------------
# Token kinds
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # Literals
    INTEGER    = auto()
    FLOAT      = auto()
    STRING     = auto()
    BOOL       = auto()

    # Identifiers / keywords
    IDENTIFIER = auto()
    LET        = auto()
    FN         = auto()
    RETURN     = auto()
    IF         = auto()
    ELSE       = auto()
    WHILE      = auto()
    PRINT      = auto()
    TRUE       = auto()
    FALSE      = auto()

    # Type keywords
    TYPE_INT    = auto()
    TYPE_FLOAT  = auto()
    TYPE_BOOL   = auto()
    TYPE_STRING = auto()

    # Arithmetic operators
    PLUS   = auto()
    MINUS  = auto()
    STAR   = auto()
    SLASH  = auto()
    PERCENT = auto()

    # Comparison operators
    EQUAL_EQUAL   = auto()
    BANG_EQUAL    = auto()
    LESS          = auto()
    LESS_EQUAL    = auto()
    GREATER       = auto()
    GREATER_EQUAL = auto()

    # Logical operators
    AND = auto()
    OR  = auto()
    NOT = auto()

    # Assignment
    EQUAL = auto()

    # Punctuation
    COLON     = auto()
    SEMICOLON = auto()
    COMMA     = auto()
    DOT       = auto()
    ARROW     = auto()   # ->

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()

    # Special
    EOF     = auto()
    NEWLINE = auto()


# Keywords mapping
KEYWORDS: dict[str, TokenType] = {
    "let":    TokenType.LET,
    "fn":     TokenType.FN,
    "return": TokenType.RETURN,
    "if":     TokenType.IF,
    "else":   TokenType.ELSE,
    "while":  TokenType.WHILE,
    "print":  TokenType.PRINT,
    "true":   TokenType.TRUE,
    "false":  TokenType.FALSE,
    "int":    TokenType.TYPE_INT,
    "float":  TokenType.TYPE_FLOAT,
    "bool":   TokenType.TYPE_BOOL,
    "string": TokenType.TYPE_STRING,
    "and":    TokenType.AND,
    "or":     TokenType.OR,
    "not":    TokenType.NOT,
}


# ---------------------------------------------------------------------------
# Token data-class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str | int | float | bool | None
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"LexerError at {line}:{column} – {message}")
        self.line = line
        self.column = column


class Lexer:
    """Converts MCPScript source text into a flat list of Tokens."""

    def __init__(self, source: str) -> None:
        self._source = source
        self._pos = 0
        self._line = 1
        self._col = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        for tok in self._scan():
            tokens.append(tok)
        return tokens

    # ------------------------------------------------------------------
    # Core scanner
    # ------------------------------------------------------------------

    def _scan(self) -> Iterator[Token]:
        while self._pos < len(self._source):
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._source):
                break

            ch = self._peek()

            # String literal
            if ch == '"':
                yield self._read_string()
            # Number literal
            elif ch.isdigit() or (ch == '.' and self._peek(1).isdigit()):
                yield self._read_number()
            # Identifier or keyword
            elif ch.isalpha() or ch == '_':
                yield self._read_identifier()
            # Multi-char / single-char operators
            else:
                yield self._read_symbol()

        yield Token(TokenType.EOF, None, self._line, self._col)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        idx = self._pos + offset
        return self._source[idx] if idx < len(self._source) else '\0'

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == '\n':
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._source):
            ch = self._peek()
            if ch in (' ', '\t', '\r', '\n'):
                self._advance()
            elif ch == '/' and self._peek(1) == '/':
                # Single-line comment
                while self._pos < len(self._source) and self._peek() != '\n':
                    self._advance()
            else:
                break

    def _read_string(self) -> Token:
        line, col = self._line, self._col
        self._advance()  # consume opening "
        buf: list[str] = []
        while self._pos < len(self._source):
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            if ch == '\n':
                raise LexerError("Unterminated string literal", line, col)
            if ch == '\\':
                self._advance()
                escape = self._advance()
                buf.append({
                    'n': '\n', 't': '\t', 'r': '\r',
                    '"': '"',  '\\': '\\',
                }.get(escape, escape))
            else:
                buf.append(self._advance())
        else:
            raise LexerError("Unterminated string literal", line, col)
        return Token(TokenType.STRING, ''.join(buf), line, col)

    def _read_number(self) -> Token:
        line, col = self._line, self._col
        buf: list[str] = []
        is_float = False
        while self._pos < len(self._source) and (self._peek().isdigit() or self._peek() == '.'):
            ch = self._peek()
            if ch == '.':
                if is_float:
                    break
                is_float = True
            buf.append(self._advance())
        raw = ''.join(buf)
        if is_float:
            return Token(TokenType.FLOAT, float(raw), line, col)
        return Token(TokenType.INTEGER, int(raw), line, col)

    def _read_identifier(self) -> Token:
        line, col = self._line, self._col
        buf: list[str] = []
        while self._pos < len(self._source) and (self._peek().isalnum() or self._peek() == '_'):
            buf.append(self._advance())
        name = ''.join(buf)
        tok_type = KEYWORDS.get(name, TokenType.IDENTIFIER)
        value: str | bool = name
        if tok_type == TokenType.TRUE:
            value = True
        elif tok_type == TokenType.FALSE:
            value = False
        return Token(tok_type, value, line, col)

    def _read_symbol(self) -> Token:
        line, col = self._line, self._col
        ch = self._advance()

        two = ch + self._peek()
        DOUBLE: dict[str, TokenType] = {
            '==': TokenType.EQUAL_EQUAL,
            '!=': TokenType.BANG_EQUAL,
            '<=': TokenType.LESS_EQUAL,
            '>=': TokenType.GREATER_EQUAL,
            '->': TokenType.ARROW,
        }
        if two in DOUBLE:
            self._advance()
            return Token(DOUBLE[two], two, line, col)

        SINGLE: dict[str, TokenType] = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '<': TokenType.LESS,
            '>': TokenType.GREATER,
            '=': TokenType.EQUAL,
            '!': TokenType.NOT,
            ':': TokenType.COLON,
            ';': TokenType.SEMICOLON,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
        }
        if ch in SINGLE:
            return Token(SINGLE[ch], ch, line, col)

        raise LexerError(f"Unexpected character {ch!r}", line, col)
