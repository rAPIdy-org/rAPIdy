<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Историческая документация rAPIdy 1.x.** Страница сохранена только для справки и может описывать aiohttp API, которых нет в rAPIdy 2.0. Для нового кода используйте [актуальную документацию 2.0](https://rapidy.dev/).

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
