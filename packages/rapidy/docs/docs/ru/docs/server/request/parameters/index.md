# HTTP-параметры
В этом разделе рассмотрим, как извлекать и проверять http-параметры с помощью **`Rapidy`**.

## Основы извлечения и валидации данных
Для проверки и извлечения данных из входящего HTTP-запроса **Rapidy** использует свои внутренние типы данных — **rapidy-параметры**.

Пример ниже извлекает и проверяет **переменную динамического пути** `user_id` и **заголовок** `Host`:

```python
{!> ./docs/docs/server/request/parameters/index/01_index.py !}
```

### Что такое rapidy-параметр?

**Rapidy-параметр** — это `мета-объект`, содержащий информацию о том, как именно будут извлекаться параметры из входящего HTTP-запроса.

Все **rapidy-параметры** находятся в модуле `rapidy.parameters.http`:

```python
{!> ./docs/docs/server/request/parameters/index/02_parameters_import/01_example.py !}
```

Также доступ к ним можно получить через модуль `rapidy.http`:

```python
{!> ./docs/docs/server/request/parameters/index/02_parameters_import/02_example.py !}
```

## Параметры http-запроса

Подробнее о каждом типе параметров можно узнать в соответствующих разделах:

- **[Path](../parameters/path)** — *параметры пути (используются для создания динамических API)*
- **[Headers](../parameters/headers)** — *параметры заголовков запроса*
- **[Cookies](../parameters/cookies)** — *параметры cookie (извлекаются из заголовков автоматически)*
- **[Query Parameters](../parameters/query)** — *параметры запроса, передаваемые в URL*
- **[Body](../parameters/body)** — *параметры тела запроса*

## Извлечение данных

Для извлечения данных используется `имя атрибута` или `alias` **rapidy-параметра**.

!!! example "Извлечение по имени атрибута"
    ```python
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/01_name_attr/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/01_name_attr/curl.sh !}
    ```

!!! example "Извлечение по alias"
    ```python
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/02_alias/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/02_alias/curl.sh !}
    ```

## Возможности валидации

Каждый **rapidy-параметр** является наследником **<a href="https://docs.pydantic.dev/latest/concepts/fields/" target="_blank">pydantic.Field</a>**
и поддерживает все его функции.

```python
{!> ./docs/docs/server/request/parameters/index/04_validation.py !}
```

## Способы аннотации параметров

### Передача параметра как значения по умолчанию
Самый простой и понятный способ аннотации:

```python
{!> ./docs/docs/server/request/parameters/index/05_param_annotation/01_as_default.py !}
```

Однако, если вы используете статические анализаторы кода, например, `mypy`, могут возникнуть ошибки:
```
main.py:4: error: Incompatible default for argument "user_id" (default has type "PathParam", argument has type
"int")  [assignment]
```

Чтобы этого избежать, включите mypy-плагин для **Rapidy**:
```toml
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- включение плагина Rapidy
]
```

### Аннотация с использованием `typing.Annotated`

Подробнее о `typing.Annotated` можно прочитать в официальной документации Python
**<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">здесь</a>**.

```python
{!> ./docs/docs/server/request/parameters/index/05_param_annotation/02_annotated.py !}
```

В аннотации `Annotated` используются два ключевых аргумента:

- <span class="base-color">Первый</span> аргумент **Annotated[<span class="success-color">int</span>, ...]** определяет ожидаемый тип данных
(в данном случае, `int`).
- <span class="base-color">Последний</span> аргумент **Annotated[..., <span class="success-color">PathParam()</span>]** должен быть одним из
HTTP-параметров **Rapidy** (`Header`, `Headers`, `Cookie`, ..., `Body`). В данном случае сервер ожидает заголовок `Host`.

!!! note ""
    Так как `Annotated` может принимать неограниченное количество параметров, **Rapidy**
    использует только **первый** и **последний** аргумент для валидации.
    Остальные параметры может использовать `pydantic` в качестве мета-информации для модели, для дополнительных проверок,
    если он их поддерживает.

!!! warning "Отсутствие HTTP-параметров в `Annotated`"
    Если `Annotated` не содержит HTTP-параметра, например, `Annotated[str, str]`,
    атрибут будет проигнорирован.

!!! note "Поддержка значений по умолчанию"
    `Header(default=..., default_factory=...)`

    Подробнее о значениях по умолчанию можно прочитать в разделе каждого http-параметра.
