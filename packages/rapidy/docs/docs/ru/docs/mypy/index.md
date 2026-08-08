# mypy
## Описание
`Rapidy` поддерживает собственный `mypy` плагин.

Чтобы включить `mypy` плагин просто добавьте его в один из файлов конфигурации.

```python
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- enable rapidy plugin
]
```
