"""
Recursive-descent parser for MCPScript.

Grammar (simplified):

    program          → statement* EOF
    statement        → var_decl | assign | if_stmt | while_stmt
                     | fn_decl | return_stmt | print_stmt | expr_stmt
    var_decl         → "let" IDENTIFIER ":" type "=" expression ";"
    assign           → IDENTIFIER "=" expression ";"
    if_stmt          → "if" expression block ( "else" block )?
    while_stmt       → "while" expression block
    fn_decl          → "fn" IDENTIFIER "(" params ")" "->" type block
    return_stmt      → "return" expression? ";"
    print_stmt       → "print" "(" expr_list ")" ";"
    expr_stmt        → expression ";"
    block            → "{" statement* "}"
    params           → ( param ( "," param )* )?
    param            → IDENTIFIER ":" type
    type             → "int" | "float" | "bool" | "string"
    expression       → or_expr
    or_expr          → and_expr ( "or" and_expr )*
    and_expr         → equality ( "and" equality )*
    equality         → comparison ( ("==" | "!=") comparison )*
    comparison       → addition ( ("<" | "<=" | ">" | ">=") addition )*
    addition         → multiplication ( ("+" | "-") multiplication )*
    multiplication   → unary ( ("*" | "/" | "%") unary )*
    unary            → ("-" | "not") unary | primary
    primary          → INTEGER | FLOAT | STRING | "true" | "false"
                     | IDENTIFIER | call_expr | "(" expression ")"
    call_expr        → IDENTIFIER "(" expr_list ")"
    expr_list        → ( expression ( "," expression )* )?
"""

from __future__ import annotations

from typing import Optional

from .lexer import Lexer, Token, TokenType
from .ast_nodes import (
    AssignStmt, BinaryExpr, Block, CallExpr, ExprStmt, Expr,
    FunctionDeclStmt, IdentifierExpr, IfStmt, LiteralExpr, Parameter,
    PrintStmt, Program, ReturnStmt, Stmt, TypeAnnotation, UnaryExpr,
    VarDeclStmt, WhileStmt,
)


class ParseError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"ParseError at {line}:{column} – {message}")
        self.line = line
        self.column = column


class Parser:
    """Converts a token stream into an AST (Program node)."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse(self) -> Program:
        stmts: list[Stmt] = []
        while not self._at_end():
            stmts.append(self._statement())
        return Program(statements=stmts, line=1, column=1)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _statement(self) -> Stmt:
        tok = self._peek()
        if tok.type == TokenType.LET:
            return self._var_decl()
        if tok.type == TokenType.FN:
            return self._fn_decl()
        if tok.type == TokenType.IF:
            return self._if_stmt()
        if tok.type == TokenType.WHILE:
            return self._while_stmt()
        if tok.type == TokenType.RETURN:
            return self._return_stmt()
        if tok.type == TokenType.PRINT:
            return self._print_stmt()
        # Peek ahead: assignment vs expression statement
        if tok.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.EQUAL:
            return self._assign_stmt()
        return self._expr_stmt()

    def _var_decl(self) -> VarDeclStmt:
        tok = self._consume(TokenType.LET)
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.COLON)
        ann = self._type_annotation()
        self._consume(TokenType.EQUAL)
        init = self._expression()
        self._consume(TokenType.SEMICOLON)
        return VarDeclStmt(
            name=str(name_tok.value),
            type_annotation=ann,
            initializer=init,
            line=tok.line,
            column=tok.column,
        )

    def _assign_stmt(self) -> AssignStmt:
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.EQUAL)
        val = self._expression()
        self._consume(TokenType.SEMICOLON)
        return AssignStmt(
            name=str(name_tok.value),
            value=val,
            line=name_tok.line,
            column=name_tok.column,
        )

    def _if_stmt(self) -> IfStmt:
        tok = self._consume(TokenType.IF)
        cond = self._expression()
        then_b = self._block()
        else_b: Optional[Block] = None
        if self._match(TokenType.ELSE):
            else_b = self._block()
        return IfStmt(condition=cond, then_branch=then_b, else_branch=else_b,
                      line=tok.line, column=tok.column)

    def _while_stmt(self) -> WhileStmt:
        tok = self._consume(TokenType.WHILE)
        cond = self._expression()
        body = self._block()
        return WhileStmt(condition=cond, body=body, line=tok.line, column=tok.column)

    def _fn_decl(self) -> FunctionDeclStmt:
        tok = self._consume(TokenType.FN)
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.LPAREN)
        params = self._params()
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.ARROW)
        ret_type = self._type_annotation()
        body = self._block()
        return FunctionDeclStmt(
            name=str(name_tok.value),
            parameters=params,
            return_type=ret_type,
            body=body,
            line=tok.line,
            column=tok.column,
        )

    def _return_stmt(self) -> ReturnStmt:
        tok = self._consume(TokenType.RETURN)
        val: Optional[Expr] = None
        if not self._check(TokenType.SEMICOLON):
            val = self._expression()
        self._consume(TokenType.SEMICOLON)
        return ReturnStmt(value=val, line=tok.line, column=tok.column)

    def _print_stmt(self) -> PrintStmt:
        tok = self._consume(TokenType.PRINT)
        self._consume(TokenType.LPAREN)
        args = self._expr_list()
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.SEMICOLON)
        return PrintStmt(arguments=args, line=tok.line, column=tok.column)

    def _expr_stmt(self) -> ExprStmt:
        expr = self._expression()
        self._consume(TokenType.SEMICOLON)
        return ExprStmt(expression=expr, line=expr.line, column=expr.column)

    def _block(self) -> Block:
        tok = self._consume(TokenType.LBRACE)
        stmts: list[Stmt] = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            stmts.append(self._statement())
        self._consume(TokenType.RBRACE)
        return Block(statements=stmts, line=tok.line, column=tok.column)

    def _params(self) -> list[Parameter]:
        params: list[Parameter] = []
        if self._check(TokenType.RPAREN):
            return params
        params.append(self._param())
        while self._match(TokenType.COMMA):
            params.append(self._param())
        return params

    def _param(self) -> Parameter:
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.COLON)
        ann = self._type_annotation()
        return Parameter(name=str(name_tok.value), type_annotation=ann,
                         line=name_tok.line, column=name_tok.column)

    def _type_annotation(self) -> TypeAnnotation:
        type_tokens = {
            TokenType.TYPE_INT:    "int",
            TokenType.TYPE_FLOAT:  "float",
            TokenType.TYPE_BOOL:   "bool",
            TokenType.TYPE_STRING: "string",
        }
        tok = self._peek()
        if tok.type in type_tokens:
            self._advance()
            return TypeAnnotation(name=type_tokens[tok.type],
                                  line=tok.line, column=tok.column)
        raise ParseError(f"Expected a type keyword, got {tok.value!r}", tok.line, tok.column)

    # ------------------------------------------------------------------
    # Expressions (precedence climbing)
    # ------------------------------------------------------------------

    def _expression(self) -> Expr:
        return self._or_expr()

    def _or_expr(self) -> Expr:
        left = self._and_expr()
        while self._check(TokenType.OR):
            op_tok = self._advance()
            right = self._and_expr()
            left = BinaryExpr(left=left, operator="or", right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _and_expr(self) -> Expr:
        left = self._equality()
        while self._check(TokenType.AND):
            op_tok = self._advance()
            right = self._equality()
            left = BinaryExpr(left=left, operator="and", right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _equality(self) -> Expr:
        left = self._comparison()
        while self._check(TokenType.EQUAL_EQUAL) or self._check(TokenType.BANG_EQUAL):
            op_tok = self._advance()
            right = self._comparison()
            left = BinaryExpr(left=left, operator=str(op_tok.value), right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _comparison(self) -> Expr:
        left = self._addition()
        cmp_types = {TokenType.LESS, TokenType.LESS_EQUAL,
                     TokenType.GREATER, TokenType.GREATER_EQUAL}
        while self._peek().type in cmp_types:
            op_tok = self._advance()
            right = self._addition()
            left = BinaryExpr(left=left, operator=str(op_tok.value), right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _addition(self) -> Expr:
        left = self._multiplication()
        while self._check(TokenType.PLUS) or self._check(TokenType.MINUS):
            op_tok = self._advance()
            right = self._multiplication()
            left = BinaryExpr(left=left, operator=str(op_tok.value), right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _multiplication(self) -> Expr:
        left = self._unary()
        mul_types = {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}
        while self._peek().type in mul_types:
            op_tok = self._advance()
            right = self._unary()
            left = BinaryExpr(left=left, operator=str(op_tok.value), right=right,
                              line=op_tok.line, column=op_tok.column)
        return left

    def _unary(self) -> Expr:
        if self._check(TokenType.MINUS):
            op_tok = self._advance()
            return UnaryExpr(operator="-", operand=self._unary(),
                             line=op_tok.line, column=op_tok.column)
        if self._check(TokenType.NOT):
            op_tok = self._advance()
            return UnaryExpr(operator="not", operand=self._unary(),
                             line=op_tok.line, column=op_tok.column)
        return self._primary()

    def _primary(self) -> Expr:
        tok = self._peek()

        if tok.type == TokenType.INTEGER:
            self._advance()
            return LiteralExpr(value=tok.value, line=tok.line, column=tok.column)

        if tok.type == TokenType.FLOAT:
            self._advance()
            return LiteralExpr(value=tok.value, line=tok.line, column=tok.column)

        if tok.type == TokenType.STRING:
            self._advance()
            return LiteralExpr(value=tok.value, line=tok.line, column=tok.column)

        if tok.type in (TokenType.TRUE, TokenType.FALSE):
            self._advance()
            return LiteralExpr(value=tok.value, line=tok.line, column=tok.column)

        if tok.type == TokenType.IDENTIFIER:
            # Look ahead for function call
            if self._peek(1).type == TokenType.LPAREN:
                return self._call_expr()
            self._advance()
            return IdentifierExpr(name=str(tok.value), line=tok.line, column=tok.column)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._expression()
            self._consume(TokenType.RPAREN)
            return expr

        raise ParseError(f"Unexpected token {tok.value!r} in expression",
                         tok.line, tok.column)

    def _call_expr(self) -> CallExpr:
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.LPAREN)
        args = self._expr_list()
        self._consume(TokenType.RPAREN)
        return CallExpr(callee=str(name_tok.value), arguments=args,
                        line=name_tok.line, column=name_tok.column)

    def _expr_list(self) -> list[Expr]:
        args: list[Expr] = []
        if self._check(TokenType.RPAREN):
            return args
        args.append(self._expression())
        while self._match(TokenType.COMMA):
            args.append(self._expression())
        return args

    # ------------------------------------------------------------------
    # Token stream utilities
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> Token:
        idx = self._pos + offset
        if idx >= len(self._tokens):
            return self._tokens[-1]   # EOF token
        return self._tokens[idx]

    def _at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _check(self, ttype: TokenType) -> bool:
        return self._peek().type == ttype

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, ttype: TokenType) -> Token:
        if self._check(ttype):
            return self._advance()
        tok = self._peek()
        raise ParseError(
            f"Expected {ttype.name} but got {tok.type.name} ({tok.value!r})",
            tok.line, tok.column,
        )
