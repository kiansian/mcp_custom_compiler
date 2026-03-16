"""Unit tests for the MCPScript lexer."""

import pytest

from src.compiler.lexer import Lexer, LexerError, Token, TokenType


def lex(source: str) -> list[Token]:
    return Lexer(source).tokenize()


def types_of(source: str) -> list[TokenType]:
    return [t.type for t in lex(source) if t.type != TokenType.EOF]


class TestLiteralTokens:
    def test_integer(self):
        toks = lex("42")
        assert toks[0].type == TokenType.INTEGER
        assert toks[0].value == 42

    def test_float(self):
        toks = lex("3.14")
        assert toks[0].type == TokenType.FLOAT
        assert pytest.approx(toks[0].value) == 3.14

    def test_string(self):
        toks = lex('"hello world"')
        assert toks[0].type == TokenType.STRING
        assert toks[0].value == "hello world"

    def test_string_escape_sequences(self):
        toks = lex(r'"line1\nline2"')
        assert toks[0].value == "line1\nline2"

    def test_bool_true(self):
        toks = lex("true")
        assert toks[0].type == TokenType.TRUE
        assert toks[0].value is True

    def test_bool_false(self):
        toks = lex("false")
        assert toks[0].type == TokenType.FALSE
        assert toks[0].value is False


class TestKeywords:
    @pytest.mark.parametrize("kw,expected", [
        ("let",    TokenType.LET),
        ("fn",     TokenType.FN),
        ("return", TokenType.RETURN),
        ("if",     TokenType.IF),
        ("else",   TokenType.ELSE),
        ("while",  TokenType.WHILE),
        ("print",  TokenType.PRINT),
        ("int",    TokenType.TYPE_INT),
        ("float",  TokenType.TYPE_FLOAT),
        ("bool",   TokenType.TYPE_BOOL),
        ("string", TokenType.TYPE_STRING),
        ("and",    TokenType.AND),
        ("or",     TokenType.OR),
        ("not",    TokenType.NOT),
    ])
    def test_keyword(self, kw, expected):
        assert types_of(kw) == [expected]

    def test_identifier_vs_keyword(self):
        assert types_of("letter") == [TokenType.IDENTIFIER]
        assert types_of("returning") == [TokenType.IDENTIFIER]


class TestOperators:
    @pytest.mark.parametrize("src,expected", [
        ("+",  TokenType.PLUS),
        ("-",  TokenType.MINUS),
        ("*",  TokenType.STAR),
        ("/",  TokenType.SLASH),
        ("%",  TokenType.PERCENT),
        ("==", TokenType.EQUAL_EQUAL),
        ("!=", TokenType.BANG_EQUAL),
        ("<=", TokenType.LESS_EQUAL),
        (">=", TokenType.GREATER_EQUAL),
        ("<",  TokenType.LESS),
        (">",  TokenType.GREATER),
        ("=",  TokenType.EQUAL),
        ("->", TokenType.ARROW),
    ])
    def test_operator(self, src, expected):
        assert types_of(src) == [expected]


class TestComments:
    def test_single_line_comment_skipped(self):
        assert types_of("// this is a comment") == []

    def test_comment_followed_by_code(self):
        toks = types_of("// comment\n42")
        assert toks == [TokenType.INTEGER]


class TestLexerErrors:
    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            lex('"unterminated')

    def test_unexpected_character(self):
        with pytest.raises(LexerError):
            lex("@")


class TestPositionTracking:
    def test_line_and_column(self):
        toks = lex("let\nx")
        assert toks[0].line == 1
        assert toks[0].column == 1
        assert toks[1].line == 2
        assert toks[1].column == 1


class TestComplexSource:
    def test_variable_declaration_tokens(self):
        tts = types_of("let x: int = 5;")
        assert tts == [
            TokenType.LET,
            TokenType.IDENTIFIER,
            TokenType.COLON,
            TokenType.TYPE_INT,
            TokenType.EQUAL,
            TokenType.INTEGER,
            TokenType.SEMICOLON,
        ]

    def test_function_declaration_tokens(self):
        src = "fn add(a: int, b: int) -> int { return a + b; }"
        tts = types_of(src)
        assert TokenType.FN in tts
        assert TokenType.ARROW in tts
        assert TokenType.RETURN in tts
