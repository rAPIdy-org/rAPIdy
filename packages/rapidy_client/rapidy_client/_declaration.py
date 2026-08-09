from __future__ import annotations

import ast
import dis
import inspect
import textwrap
from collections.abc import Callable
from typing import Any

_IGNORED_BYTECODE = frozenset(
    {
        "CACHE",
        "COPY_FREE_VARS",
        "EXTENDED_ARG",
        "NOP",
        "POP_TOP",
        "RESUME",
        "RETURN_GENERATOR",
    }
)
_ALLOWED_RAISE_BYTECODE = frozenset(
    {
        "CALL",
        "LOAD_GLOBAL",
        "PRECALL",
        "PUSH_NULL",
        "RAISE_VARARGS",
    }
)


def _is_not_implemented_raise(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Raise):
        return False
    raised = statement.exc
    return (isinstance(raised, ast.Name) and raised.id == "NotImplementedError") or (
        isinstance(raised, ast.Call)
        and isinstance(raised.func, ast.Name)
        and raised.func.id == "NotImplementedError"
        and not raised.args
        and not raised.keywords
    )


def _source_body_is_declarative(func: Callable[..., Any]) -> bool | None:
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    except (OSError, SyntaxError, TypeError):
        return None

    node = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.AsyncFunctionDef) and item.name == func.__name__
        ),
        None,
    )
    if node is None:
        return None

    body = list(node.body)
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body.pop(0)
    if not body:
        return True
    if len(body) != 1:
        return False
    statement = body[0]
    if isinstance(statement, ast.Pass):
        return True
    if isinstance(statement, ast.Expr):
        value = statement.value
        return isinstance(value, ast.Constant) and value.value is Ellipsis
    return _is_not_implemented_raise(statement)


def _bytecode_body_is_declarative(func: Callable[..., Any]) -> bool:
    instructions = [
        instruction
        for instruction in dis.get_instructions(func)
        if instruction.opname not in _IGNORED_BYTECODE
        and not (
            instruction.opname == "CALL_INTRINSIC_1"
            and "STOPITERATION_ERROR" in instruction.argrepr
        )
        and instruction.opname != "RERAISE"
    ]

    if len(instructions) == 1:
        instruction = instructions[0]
        return instruction.opname == "RETURN_CONST" and instruction.argval is None
    if len(instructions) == 2:
        load, return_value = instructions
        if (
            load.opname == "LOAD_CONST"
            and load.argval is None
            and return_value.opname == "RETURN_VALUE"
        ):
            return True

    if not instructions or any(
        instruction.opname not in _ALLOWED_RAISE_BYTECODE
        for instruction in instructions
    ):
        return False
    if instructions[-1].opname != "RAISE_VARARGS" or instructions[-1].arg != 1:
        return False
    globals_loaded = [
        instruction for instruction in instructions if instruction.opname == "LOAD_GLOBAL"
    ]
    calls = [instruction for instruction in instructions if instruction.opname == "CALL"]
    return (
        len(globals_loaded) == 1
        and globals_loaded[0].argval == "NotImplementedError"
        and len(calls) <= 1
        and all(instruction.arg == 0 for instruction in calls)
    )


def declaration_body_is_declarative(func: Callable[..., Any]) -> bool:
    """Validate a declaration from source, falling back to conservative bytecode."""
    source_result = _source_body_is_declarative(func)
    if source_result is not None:
        return source_result
    return _bytecode_body_is_declarative(func)
