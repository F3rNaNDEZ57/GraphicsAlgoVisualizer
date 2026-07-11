"""Pseudocode interpreter: a restricted Python subset, parsed with ``ast``
and walked by a hand-written generator-based evaluator (not ``exec``).

The evaluator yields once per visualization builtin call (see
``builtins_registry.VIZ_BUILTIN_METHODS``), so a caller can step through an
algorithm one visible action at a time instead of running it to completion.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Iterator

from .builtins_registry import resolve_builtin
from .errors import PseudocodeError

_ALLOWED_NODES = (
    ast.Module,
    ast.Assign,
    ast.AugAssign,
    ast.If,
    ast.While,
    ast.For,
    ast.BinOp,
    ast.Compare,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Call,
    ast.Expr,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Subscript,
    ast.Load,
    ast.Store,
    ast.keyword,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.And,
    ast.Or,
    ast.Not,
    ast.USub,
    ast.UAdd,
)

_BINOPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_CMPOPS: dict[type, Any] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_UNARYOPS: dict[type, Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
}


class Interpreter:
    """Parses and runs one pseudocode source against a Canvas."""

    def __init__(self, source: str, canvas: Any):
        self.canvas = canvas
        self.env: dict[str, Any] = {}
        try:
            self.tree = ast.parse(source, mode="exec")
        except SyntaxError as exc:
            raise PseudocodeError(f"syntax error: {exc.msg}", lineno=exc.lineno) from exc
        self._validate(self.tree)

    def run(self) -> Iterator[None]:
        """Generator; yields once per visualization builtin call."""
        yield from self._exec_body(self.tree.body)

    # -- validation --------------------------------------------------

    def _validate(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                raise PseudocodeError(
                    f"unsupported syntax: {type(node).__name__}",
                    lineno=getattr(node, "lineno", None),
                )
            if isinstance(node, ast.For):
                if not isinstance(node.target, ast.Name):
                    raise PseudocodeError(
                        "'for' loop target must be a single variable", lineno=node.lineno
                    )

    # -- statement execution ------------------------------------------

    def _exec_body(self, stmts: list[ast.stmt]) -> Iterator[None]:
        for stmt in stmts:
            yield from self._exec_stmt(stmt)

    def _exec_stmt(self, stmt: ast.stmt) -> Iterator[None]:
        if isinstance(stmt, ast.Assign):
            value = self._eval_expr(stmt.value)
            for target in stmt.targets:
                self._assign(target, value)
            return

        if isinstance(stmt, ast.AugAssign):
            current = self._eval_expr(self._as_load(stmt.target))
            value = self._eval_expr(stmt.value)
            new_value = self._apply_binop(stmt.op, current, value)
            self._assign(stmt.target, new_value)
            return

        if isinstance(stmt, ast.If):
            branch = stmt.body if self._eval_expr(stmt.test) else stmt.orelse
            yield from self._exec_body(branch)
            return

        if isinstance(stmt, ast.While):
            while self._eval_expr(stmt.test):
                yield from self._exec_body(stmt.body)
            return

        if isinstance(stmt, ast.For):
            iterable = self._eval_expr(stmt.iter)
            if not isinstance(iterable, (range, list, tuple)):
                raise PseudocodeError(
                    f"'for' loop must iterate over range(...) or a list, got {type(iterable).__name__}",
                    lineno=stmt.lineno,
                )
            for i in iterable:
                self.env[stmt.target.id] = i
                yield from self._exec_body(stmt.body)
            return

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            yield from self._exec_call_stmt(stmt.value)
            return

        raise PseudocodeError(
            f"unsupported statement: {type(stmt).__name__}", lineno=getattr(stmt, "lineno", None)
        )

    def _exec_call_stmt(self, call: ast.Call) -> Iterator[None]:
        name = self._call_name(call)
        args = [self._eval_expr(a) for a in call.args]
        kwargs = {kw.arg: self._eval_expr(kw.value) for kw in call.keywords}
        builtin = resolve_builtin(name, self.canvas)
        builtin.invoke(*args, **kwargs)
        if builtin.is_viz:
            yield

    def _assign(self, target: ast.expr, value: Any) -> None:
        if isinstance(target, ast.Name):
            self.env[target.id] = value
            return
        if isinstance(target, ast.Subscript):
            container = self._eval_expr(target.value)
            index = self._eval_expr(target.slice)
            container[index] = value
            return
        raise PseudocodeError(
            f"unsupported assignment target: {type(target).__name__}",
            lineno=getattr(target, "lineno", None),
        )

    @staticmethod
    def _as_load(target: ast.expr) -> ast.expr:
        # AugAssign targets carry Store ctx; reuse the same node to read the
        # current value since our evaluator doesn't branch on ctx.
        return target

    # -- expression evaluation -----------------------------------------

    def _eval_expr(self, node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise PseudocodeError(f"undefined variable '{node.id}'", lineno=node.lineno)
            return self.env[node.id]
        if isinstance(node, ast.BinOp):
            left = self._eval_expr(node.left)
            right = self._eval_expr(node.right)
            return self._apply_binop(node.op, left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_expr(node.operand)
            return self._apply_unaryop(node.op, operand)
        if isinstance(node, ast.BoolOp):
            values = [self._eval_expr(v) for v in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare):
            return self._eval_compare(node)
        if isinstance(node, ast.List):
            return [self._eval_expr(e) for e in node.elts]
        if isinstance(node, ast.Subscript):
            container = self._eval_expr(node.value)
            index = self._eval_expr(node.slice)
            return container[index]
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        raise PseudocodeError(
            f"unsupported expression: {type(node).__name__}", lineno=getattr(node, "lineno", None)
        )

    def _eval_call(self, call: ast.Call) -> Any:
        name = self._call_name(call)
        builtin = resolve_builtin(name, self.canvas)
        if builtin.is_viz:
            raise PseudocodeError(
                f"'{name}' is a visualization action and cannot be used inside an expression",
                lineno=call.lineno,
            )
        args = [self._eval_expr(a) for a in call.args]
        kwargs = {kw.arg: self._eval_expr(kw.value) for kw in call.keywords}
        return builtin.invoke(*args, **kwargs)

    def _call_name(self, call: ast.Call) -> str:
        if not isinstance(call.func, ast.Name):
            raise PseudocodeError(
                "only direct function calls are supported", lineno=call.lineno
            )
        return call.func.id

    def _eval_compare(self, node: ast.Compare) -> bool:
        left = self._eval_expr(node.left)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_expr(comparator)
            fn = _CMPOPS.get(type(op))
            if fn is None:
                raise PseudocodeError(f"unsupported comparator: {type(op).__name__}")
            result = result and fn(left, right)
            left = right
        return result

    @staticmethod
    def _apply_binop(op: ast.operator, left: Any, right: Any) -> Any:
        fn = _BINOPS.get(type(op))
        if fn is None:
            raise PseudocodeError(f"unsupported operator: {type(op).__name__}")
        return fn(left, right)

    @staticmethod
    def _apply_unaryop(op: ast.unaryop, operand: Any) -> Any:
        fn = _UNARYOPS.get(type(op))
        if fn is None:
            raise PseudocodeError(f"unsupported operator: {type(op).__name__}")
        return fn(operand)
