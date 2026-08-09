<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Legacy rAPIdy 1.x documentation.** This page is retained only for historical reference and may describe aiohttp APIs that do not exist in rAPIdy 2.0. Use the [current 2.0 documentation](https://rapidy.dev/) for new code.

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
