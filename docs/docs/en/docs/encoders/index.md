# JSONIFY
## Description
**jsonify** is a `Rapidy` encoder used for converting complex Python objects
into simpler Python objects or strings.

!!! tip "`jsonify` greatly simplifies the process of saving and sending complex data."

```python
{!> ./docs/docs/encoders/index.py !}
```

**jsonify** allows you to convert any `python` object into a string or a simpler object that can be
converted to a `json` format.

!!! tip "You can use `jsonify` to prepare data for saving to a database (for example, for `MongoDB`/`Redis` or as a `JSON`/`JSONB` field in `Postgres`)."

!!! info "`Rapidy` also uses `jsonify` internally when preparing server responses."

!!! note "`Decimal` is always converted to a string."

## `jsonify` Attributes
### obj
**obj**: `Any` — the object to be converted *(can be practically anything)*.

### include
**include**: `set[str] | dict[str, Any] | None = None` — Pydantic's `include` parameter, passed to Pydantic models
to specify the fields to include.
```python hl_lines="10"
{!> ./docs/docs/encoders/attrs/include.py !}
```

---

### exclude
**exclude**: `set[str] | dict[str, Any] | None = None` — Pydantic's `exclude` parameter, passed to Pydantic models
to specify the fields to exclude.
```python hl_lines="10"
{!> ./docs/docs/encoders/attrs/exclude.py !}
```

### by_alias
**by_alias**: `bool = True` — Pydantic's `by_alias` parameter, passed to Pydantic models to determine whether to use
the alias names *(if provided)* or the Python attribute names in the output.
```python hl_lines="9 17"
{!> ./docs/docs/encoders/attrs/by_alias.py !}
```

---

### exclude_unset
**exclude_unset**: `bool = False` — Pydantic's `exclude_unset` parameter, passed to Pydantic models to determine
whether to exclude fields that were not explicitly set *(and only have default values)* from the output.
```python hl_lines="10 18"
{!> ./docs/docs/encoders/attrs/exclude_unset.py !}
```

---

### exclude_defaults
**exclude_defaults**: `bool = False` — Pydantic's `exclude_defaults` parameter, passed to Pydantic models to
determine whether to exclude fields with default values, even if they were explicitly set.
```python hl_lines="9"
{!> ./docs/docs/encoders/attrs/exclude_defaults.py !}
```

---

### exclude_none
**exclude_none**: `bool = False` — Pydantic's `exclude_none` parameter, passed to Pydantic models to determine
whether to exclude fields with a `None` value from the output.
```python hl_lines="10 18"
{!> ./docs/docs/encoders/attrs/exclude_none.py !}
```

---

### charset
**charset**: `str = 'utf-8'` — the character set to be used for encoding and decoding the `obj` data.
```python hl_lines="6 8"
{!> ./docs/docs/encoders/attrs/charset.py !}
```

---

### dumps
**dumps**: `bool = True` — a flag determining whether to convert the created object into a string. Can be set to `False` if
the object is already a `json` string.
```python hl_lines="3 4"
{!> ./docs/docs/encoders/attrs/dumps.py !}
```

---

### dumps_encoder
**dumps_encoder**: `Callable = json.dumps` — any callable object that takes an object and returns a JSON string.
```python hl_lines="9"
{!> ./docs/docs/encoders/attrs/dumps_encoder.py !}
```

---

### custom_encoder
**custom_encoder**: `Dict[Any, Callable[Any], Any]] | None = None` — Pydantic's `custom_encoder` parameter, passed to Pydantic models to
define a custom encoder.
