# Dependency Injection

Поддерживаемый DI-фасад экспортируется из `rapidy.depends`; напрямую импортировать Dishka для обычного приложения не
нужно.

```python
from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def service_name(self) -> str:
        return 'users'


@get('/context')
async def context(service_name: FromDI[str]) -> dict[str, str]:
    return {'service': service_name}


app = Rapidy(di_providers=[AppProvider()], http_route_handlers=[context])
```

- `Scope.APP` — один объект на процесс приложения, не на кластер workers.
- `Scope.REQUEST` — один объект на HTTP-запрос; финализатор вызывается после отправки/завершения ответа.
- `Scope.SESSION` — один объект на WebSocket-соединение; финализация выполняется при close, disconnect или ошибке.

Dishka передаёт обработанное исключение запроса обратно в async-generator provider как значение выражения `yield`.
Используйте этот результат для commit/rollback транзакции; `try/except` вокруг `yield` не эквивалентен этому контракту,
поскольку исключение не возбуждается внутри генератора:

```python
from collections.abc import AsyncGenerator

from rapidy.depends import provide, Provider, Scope


class DatabaseProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def transaction(self) -> AsyncGenerator[Transaction, BaseException | None]:
        transaction = await begin_transaction()
        outcome = yield transaction
        if outcome is None:
            await transaction.commit()
        else:
            await transaction.rollback()
```

Outcome охватывает исключения, преобразованные rAPIdy в HTTP error response, и необработанные ошибки handler-а.
Cancellation продолжает распространяться наружу, а provider получает тот же cancellation outcome при cleanup.

Вложенные `HTTPRouter` используют request scope корневого контейнера. Полный пример:
[`examples/di.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/di.py).
