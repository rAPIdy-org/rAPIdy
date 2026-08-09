import importlib.util
import py_compile
import sys
from pathlib import Path
from types import ModuleType

import pytest
from rapidy_client import SchemaDefinitionError
from rapidy_client.schema import PathParam, controller, get


def _load_sourceless_module(tmp_path: Path, name: str, source: str) -> ModuleType:
    source_path = tmp_path / f"{name}.py"
    bytecode_path = tmp_path / f"{name}.pyc"
    source_path.write_text(source, encoding="utf-8")
    py_compile.compile(str(source_path), cfile=str(bytecode_path), doraise=True)
    source_path.unlink()
    spec = importlib.util.spec_from_file_location(name, bytecode_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_unmarked_argument_fails_at_decoration() -> None:
    async def invalid(value: int) -> None:
        raise NotImplementedError

    with pytest.raises(SchemaDefinitionError, match="value"):
        get("/invalid")(invalid)


def test_missing_and_extra_path_parameters_fail_at_decoration() -> None:
    async def missing() -> None:
        raise NotImplementedError

    with pytest.raises(SchemaDefinitionError, match="user_id"):
        get("/users/{user_id}")(missing)

    async def extra(user_id: str = PathParam()) -> None:
        raise NotImplementedError

    with pytest.raises(SchemaDefinitionError, match="user_id"):
        get("/users")(extra)


def test_sync_and_real_body_logic_fail_at_decoration() -> None:
    def sync() -> None:
        pass

    with pytest.raises(SchemaDefinitionError, match="sync"):
        get("/sync")(sync)  # type: ignore[arg-type]

    async def real_logic() -> None:
        return None

    with pytest.raises(SchemaDefinitionError, match="real_logic"):
        get("/logic")(real_logic)

    async def wrong_raise() -> None:
        raise ValueError

    with pytest.raises(SchemaDefinitionError, match="wrong_raise"):
        get("/raise")(wrong_raise)


def test_http_ws_and_sse_declarations_load_from_sourceless_bytecode(tmp_path: Path) -> None:
    module = _load_sourceless_module(
        tmp_path,
        "bytecode_declarations",
        """
from rapidy_client import sse, ws
from rapidy_client.schema import get

@get("/health")
async def health() -> None:
    pass

@ws("/socket")
async def socket() -> None:
    raise NotImplementedError

@sse("/events")
async def events() -> None:
    ...
""",
    )

    assert module.health.declaration.path_template == "/health"
    assert module.socket.path == "/socket"
    assert module.events.path == "/events"


def test_sourceless_bytecode_still_rejects_real_declaration_logic(tmp_path: Path) -> None:
    with pytest.raises(SchemaDefinitionError, match="body must contain only"):
        _load_sourceless_module(
            tmp_path,
            "invalid_bytecode_declaration",
            """
from rapidy_client.schema import get

@get("/health")
async def health() -> None:
    print("this body would never run")
""",
        )


def test_status_conflict_fails_at_decoration() -> None:
    async def declaration() -> None:
        raise NotImplementedError

    with pytest.raises(SchemaDefinitionError, match="409"):
        get("/conflict", statuses={409: None}, error_model={409: object})(declaration)


def test_controller_method_requires_self() -> None:
    with pytest.raises(SchemaDefinitionError, match="self"):

        @controller("/api")
        class Invalid:
            @get("/ping")
            async def ping() -> None:
                raise NotImplementedError
