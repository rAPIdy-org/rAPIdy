# How to annotate

## Параметр, как значение по умолчанию

Этот способ определения является самым простым и понятным.

```Python
@routes.get('/{user_id}')
async def handler(
    user_id: int = web.PathParam(),
) -> ...:
```

Но, если вы пользуетесь статистическими анализаторами кода (такими как `mypy`), у вас могут возникнуть проблемы, 
при статической проверке вашего кода:
```
main.py:4: error: Incompatible default for argument "user_id" (default has type "PathParam", argument has type
"int")  [assignment]
```
Для того, чтобы этого избежать включите mypy-плагин для rapidy.
```toml
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- enable rapidy plugin
]
```

!!! note "Параметры поддерживают значения по умолчанию"
    `web.Header(default=..., default_factory=...)`

    Подробнее можно прочитать **[здесь](../default)**.


## Аннотация с помощью `typing.Annotated`

Про тип `typing.Annotated` можно прочитать в официальной документации `Python` 
**<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">здесь</a>**.

```Python
@routes.get('/{user_id}')
async def handler(
    user_id: Annotated[int, web.PathParam()],
) -> ...:
```
```

<span class="base-color">Первый</span> аргумент **Annotated[<span class="success-color">str</span>, ...]** 
обозначает тип, который будет использоваться для валидации входных данных.
В данном случае, сервер ожидает тип данных <span class="success-color">str</span>.

<span class="base-color">Второй</span> аргумент **Annotated[..., <span class="success-color">web.Header(alias="Host")</span>]** 
всегда должен быть инстансом одного из http-параметров Rapidy (web.Header, web.Headers, web.Cookie, ..., web.Body). 
В данном случае, сервер ожидает получение заголовка `Host`.

Если второй аргумент не является http-параметром Rapidy, например, <br/>`Annotated[str, str]`, то он просто будет пропущен.

??? note "Дополнительная мета-информация в Annotated"
    Иногда для мета-программирования, есть необходимость пробросить еще какую-информацию в параметр.
    Rapidy позволяет это сделать:
    `Annotated[str, <rapidy_param>, MetaInfo1, SomeMetaInfo2, ...]`.

    В 99.9% функция бесполезна, но она есть.

!!! note "Параметры поддерживают значения по умолчанию"
    `web.Header(default=..., default_factory=...)`

    Подробнее можно прочитать **[здесь](../default)**.
