# JSONIFY
## Описание
**jsonify** — это `Rapidy`-кодировщик, используется для преобразования сложных python-объектов
к более простым python-объектам или строке.

!!! tip "`jsonify` сильно упрощает процесс сохранения и отправки сложных данных."

```python
{!> ./docs/docs/encoders/index.py !}
```

**jsonify** позволяет преобразовывать любой объект `python` в строку или более простой объект, который может быть
преобразован в формат `json`.

!!! tip "Вы можете использовать `jsonify`, чтобы подготовить данные для сохранения в базу данных (например, для `MongoDB`/`Redis` или как поле `JSON`/`JSONB` в `Postgres`)."

!!! info "`Rapidy` также использует `jsonify` внутри себя при подготовке серверных ответов."

!!! note "`Decimal` всегда преобразуется в строку."

## Атрибуты `jsonify`
### obj
**obj**: `Any` — объект для преобразования *(может быть практически чем угодно)*.

### include
**include**: `set[str] | dict[str, Any] | None = None` — параметр Pydantic `include`, передаваемый моделям Pydantic
для указания полей, которые нужно включить.
```python hl_lines="10"
{!> ./docs/docs/encoders/attrs/include.py !}
```

---

### exclude
**exclude**: `set[str] | dict[str, Any] | None = None` — параметр Pydantic `exclude`, передаваемый моделям Pydantic
для указания полей, которые нужно исключить.
```python hl_lines="10"
{!> ./docs/docs/encoders/attrs/exclude.py !}
```

### by_alias
**by_alias**: `bool = True` — параметр Pydantic `by_alias`, передаваемый моделям Pydantic, чтобы определить, использовать ли при
выводе имена псевдонимов *(если они предоставлены)* или имена атрибутов Python.
```python hl_lines="9 17"
{!> ./docs/docs/encoders/attrs/by_alias.py !}
```

---

### exclude_unset
**exclude_unset**: `bool = False` — параметр Pydantic `exclude_unset`, передаваемый моделям Pydantic для определения,
должен ли он исключать из вывода поля, которые не были явно заданы *(и имели только значения по умолчанию)*.
```python hl_lines="10 18"
{!> ./docs/docs/encoders/attrs/exclude_unset.py !}
```

---

### exclude_defaults
**exclude_defaults**: `bool = False` — параметр Pydantic `exclude_defaults`, передаваемый моделям Pydantic, чтобы
определить, нужно ли исключать из вывода поля, которые имеют одинаковое значение по умолчанию, даже если
они были заданы явно.
```python hl_lines="9"
{!> ./docs/docs/encoders/attrs/exclude_defaults.py !}
```

---

### exclude_none
**exclude_none**: `bool = False` — параметр Pydantic `exclude_none`, передаваемый моделям Pydantic для определения,
нужно ли исключать из вывода поля, имеющие значение `None`.
```python hl_lines="10 18"
{!> ./docs/docs/encoders/attrs/exclude_none.py !}
```

---

### charset
**charset**: `str = 'utf-8'` — набор символов, который будет использоваться для кодирования и декодирования данных obj.
```python hl_lines="6 8"
{!> ./docs/docs/encoders/attrs/charset.py !}
```

---

### dumps
**dumps**: `bool = True` — флаг, который определяет, нужно ли делать из созданного объекта строку. Можно указать `False`, если
объект уже является `json`-строкой.
```python hl_lines="3 4"
{!> ./docs/docs/encoders/attrs/dumps.py !}
```

---

### dumps_encoder
**dumps_encoder**: `Callable = json.dumps` — любой вызываемый объект, который принимает объект и возвращает строку JSON.
```python hl_lines="9"
{!> ./docs/docs/encoders/attrs/dumps_encoder.py !}
```

---

### custom_encoder
**custom_encoder**: `Dict[Any, Callable[Any], Any]] | None = None` — параметр Pydantic `custom_encoder`, передаваемый в модели Pydantic для
определения пользовательского кодировщика.
