# mypy
## Description
`Rapidy` supports its own `mypy` plugin.

To enable the `mypy` plugin, simply add it to one of the configuration files.

```python
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- enable rapidy plugin
]
```
