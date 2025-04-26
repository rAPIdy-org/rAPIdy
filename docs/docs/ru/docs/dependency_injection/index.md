# Dependency Injection

`Rapidy` использует библиотеку [dishka](https://dishka.readthedocs.io/en/stable/) в качестве встроенного механизма внедрения зависимостей (Dependency Injection, DI).

Мы стремились выбрать DI-библиотеку, соответствующую философии `Rapidy`: простота, скорость, прозрачность и масштабируемость.
`dishka` идеально вписалась в эти принципы, предоставляя разработчикам мощный инструмент без лишней сложности.

`dishka` — современная и лёгкая библиотека для асинхронного внедрения зависимостей в Python-приложениях. Она ориентирована на высокую производительность, минимализм и гибкость настройки, что делает её идеальной для использования в веб-фреймворках нового поколения, таких как `Rapidy`.

Её ключевые преимущества:

- **Нативная поддержка asyncio**: полная поддержка `async`/`await`, корректное управление жизненным циклом зависимостей.
- **Минималистичная архитектура**: компактное ядро, без магии и избыточных абстракций — управление зависимостями прозрачно и предсказуемо.
- **Незаметность для бизнес-логики**: внедрение через аннотации типов (`FromDI`).
- **Гибкое управление областями видимости (scopes)**: `App`, `Session`, `Request` и др.
- **Разнообразие провайдеров**: фабрики, объекты, асинхронные функции.
- **Контекстное внедрение**: возможность передавать динамический контекст — например, для текущего пользователя.
- **Интеграция с фреймворками**: `aiohttp`, `FastStream`, `Rapidy` и другие.
- **Удобство тестирования**: провайдеры легко заменяются в тестах, без сторонних моков и патчей.

!!! tip "В `Rapidy` dishka доступна «из коробки» — дополнительная настройка не требуется."

## Примеры использования dishka в Rapidy

### Простой пример внедрения зависимости

В `Rapidy` доступна обёртка `FromDI` _(alias для `FromDishka`)_, которую можно использовать для инжекта зависимостей:

```python
{!> ./docs/docs/dependency_injection/simple_ex.py !}
```

Что здесь происходит:

1. **Определение провайдера**
   Класс `FooProvider` наследуется от `Provider` и определяет зависимость `c` типа `int`, создаваемую на каждый запрос (`Scope.REQUEST`).

2. **Регистрация обработчика запроса**
   Декоратор `@get('/')` регистрирует функцию `handler` как обработчик GET-запросов по пути `/`.

3. **Внедрение зависимости в обработчик**
   Аргумент `c: FromDI[int]` сообщает, что `c` должен быть получен из DI-контейнера на момент вызова.

4. **Создание приложения**
   Экземпляр `Rapidy` создаётся с обработчиком `handler` и провайдером `FooProvider`.

### Пример с SQLAlchemy-сессией

??? example "Откройте пример"
    ```python
    {!> ./docs/docs/dependency_injection/sa_example.py !}
    ```

## Способы инжекта

Для внедрения зависимостей используйте `rapidy.depends.FromDI` _(или `dishka.FromDishka`)_ и `rapidy.depends.FromComponent` _(или `dishka.FromComponent`)_.

```python hl_lines="11 15"
{!> ./docs/docs/dependency_injection/use_from_di.py !}
```

```python hl_lines="13 17"
{!> ./docs/docs/dependency_injection/use_from_component.py !}
```

## Особенности

### Доступ к контейнеру

Получить текущий асинхронный контейнер можно через корневое приложение `Rapidy`. Из дочернего приложения он будет равен `None`.

```python
{!> ./docs/docs/dependency_injection/get_di_container.py !}
```

### Обработчики и middleware

`dishka` полностью интегрирована с `Rapidy`, и поддерживает автоинжект во всех видах обработчиков:

```python
# providers.py
{!> ./docs/docs/dependency_injection/handlers/providers.py !}
```

**Контроллеры:**

```python
{!> ./docs/docs/dependency_injection/handlers/controller.py !}
```

**View-классы:**

```python
{!> ./docs/docs/dependency_injection/handlers/view.py !}
```

**Middleware:**

```python
{!> ./docs/docs/dependency_injection/handlers/middleware.py !}
```

### Дополнительно

- Если у первого аргумента обработчика нет аннотации, `Rapidy` пропустит его и продолжит инжект.
- Поддерживаются все возможности `dishka`: фабрики, вложенные провайдеры, контроль жизненного цикла и явное получение зависимостей.

### Внешний контейнер

Вы можете вручную передать свой `AsyncContainer` — например, если контейнер создаётся заранее и используется в разных местах.

```python
{!> ./docs/docs/dependency_injection/external_container.py !}
```

В этом случае:

- `Rapidy` не создаёт контейнер.
- Все `di_*` параметры игнорируются.
- Контейнер необходимо закрывать вручную.

## Ограничения dishka

`dishka` работает только с HTTP-обработчиками и middleware. Если вы используете контейнер и в `faststream`, и в `rapidy`, в `faststream` потребуется явное использование `@inject`.

## Атрибуты Rapidy (Application) для управления DI

##### di_container

Внешний контейнер зависимостей.

```python
di_container: AsyncContainer | None = None
```

!!! note "Если передан `di_container`, новый контейнер создан не будет."

!!! tip "Документация Dishka — [container](https://dishka.readthedocs.io/en/stable/container/index.html)."

---

##### di_providers

Список провайдеров для регистрации.

```python
di_providers: Sequence[BaseProvider] = ()
```

!!! note "Игнорируется, если передан `di_container`."

!!! tip "Документация Dishka — [providers](https://dishka.readthedocs.io/en/stable/provider/index.html)."

---

##### di_scopes

Класс области видимости (scope).

```python
di_scopes: type[BaseScope] = Scope
```

!!! tip "Документация Dishka — [scopes](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_context

Дополнительный контекст для провайдеров.

```python
di_context: dict[Any, Any] | None = None
```

!!! tip "Документация Dishka — [context](https://dishka.readthedocs.io/en/stable/advanced/context.html)."

---

##### di_lock_factory

Фабрика для блокировок контейнера.

```python
di_lock_factory: Callable[[], contextlib.AbstractAsyncContextManager[Any]] | None = Lock
```

!!! tip "Документация Dishka — [lock_factory](https://dishka.readthedocs.io/en/stable/container/index.html)."

```python
{!> ./docs/docs/server/application/di_lock_factory.py !}
```

---

##### di_skip_validation

Флаг, отключающий проверку типов провайдеров.

```python
di_skip_validation: bool = False
```

!!! tip "Документация Dishka — [skip_validation](https://dishka.readthedocs.io/en/stable/advanced/components.html)."

---

##### di_start_scope

Начальный scope контейнера.

```python
di_start_scope: BaseScope | None = None
```

!!! tip "Документация Dishka — [start_scope](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_validation_settings

Настройки валидации контейнера.

```python
di_validation_settings: ValidationSettings = DEFAULT_VALIDATION
```

!!! tip "Документация Dishka — [alias](https://dishka.readthedocs.io/en/latest/provider/alias.html)."
!!! tip "Документация Dishka — [from_context](https://dishka.readthedocs.io/en/latest/provider/from_context.html)."
!!! tip "Документация Dishka — [provide](https://dishka.readthedocs.io/en/latest/provider/provide.html)."
