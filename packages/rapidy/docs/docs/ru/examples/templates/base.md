# Базовый пример-шаблон приложения

Полностью пример можно найти <a href="https://github.com/rAPIdy-org/rAPIdy/tree/main/docs/examples/projects/base" target="blank">здесь</a>
_(`docs/examples/projects/base`)_.

!!! info "Вы можете брать этот шаблон и продолжать в нем разработку как есть."

## Structure
Структура проекта
```shell
├── .gitignore
├── .pre-commit-config.yaml
├── .env
├── pyproject.toml
├── src
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py
│   ├── application.py
│   ├── config.py
│   ├── di.py
│   ├── providers.py
│   └── middlewares.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── pytest.ini
    └── test_api
        ├── __init__.py
        └── test_hello.py

```

### .gitignore
`.gitignore` - файл сообщает Git, какие файлы и каталоги игнорировать при фиксации изменений.

---

### .pre-commit-config.yaml
`.pre-commit-config.yaml` - файл с предустановленными форматерами, линтерами и тайп-чекерами.
```yaml
{!> ./projects/base/.pre-commit-config.yaml !}
```

---

### .env
`.env` - файл с `env` для локальной разработки _(не фиксируйте и не отправляете его на гит)_.
```env
{!> ./projects/base/.env !}
```

---

### pyproject.toml
`pyproject.toml` - файл описывающий всю конфигурацию проекта: зависимости, конфигурации линтеров и прочее.
```toml
{!> ./projects/base/pyproject.toml !}
```
---

### src
`src` - основная папка проекта.

---

#### `__main__.py`
`__main__.py` - точка входа / запуска приложения.
```python
{!> ./projects/base/src/__main__.py !}
```
---

#### api.py
`api.py` - конечные http-точки приложения.
```python
{!> ./projects/base/src/api.py !}
```
---

#### application.py
`application.py` - создание приложения.
```python
{!> ./projects/base/src/application.py !}
```
---

#### config.py
`config.py` - конфигурация приложения.

Для конфигурации `env` был выбран <a href="https://github.com/pydantic/pydantic-settings" target="blank">pydantic_settings</a>.

```python
{!> ./projects/base/src/config.py !}
```

---

#### di.py
`di.py` - функции для управления инъекцией зависимостей (DI).

Над **dishka** проведены небольшие манипуляции, чтобы `inject` работал свободно по коду и позволял делать инжект в любой
асинхронную функцию или асинхронный метод проекта.

!!! note "Если вам нужен `@inject` берите его из этого модуля."

??? example "Пример инжекта конфигурации:"
    ```python
    from dishka import FromDishka as Depends
    from src.di import inject
    from src.config import Config

    @inject
    async def any_async(
        config: Depends[Config],
    ) -> ...: ...
    ```

```python
{!> ./projects/base/src/di.py !}
```

---

#### providers.py
`providers.py` - провайдеры DI.
```python
{!> ./projects/base/src/providers.py !}
```

---

#### middlewares.py
`middlewares.py` - промежуточные ПО приложения.
```python
{!> ./projects/base/src/middlewares.py !}
```

---

### tests
`tests` - папка с тестами проекта.

---

#### `conftest.py`
`conftest.py` - модуль содержащий базовые фикстуры, именно в нем будет происходить в дальнейшем подключение плагинов.
```python
{!> ./projects/base/tests/conftest.py !}
```

---

#### `pytest.ini`
`pytest.ini` - файл конфигурации `pytest`.
```python
{!> ./projects/base/tests/pytest.ini !}
```

---

#### `test_api`
`test_api` - модуль в котором тестируются `api` приложения.

---

##### `test_hello`
`test_hello` - пример простого теста.
```python
{!> ./projects/base/tests/test_api/test_hello.py !}
```
