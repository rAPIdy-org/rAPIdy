import pytest
from rapidy_client import SchemaDefinitionError
from rapidy_client.schema import PathParam, controller, get


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
