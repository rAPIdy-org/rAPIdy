---
hide:
  - navigation
  - toc
---

<style>
    .md-content .md-typeset h1 { display: none; }
</style>

<p align="center">
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">
        <img src="../assets/logo-teal.png" alt="rAPIdy">
    </a>
</p>

<p align="center">
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/dm/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Package downloads">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/v/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2&label=pypi%20rAPIdy" alt="Package version">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/pyversions/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Python versions">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v1.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V1">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V2">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a>
        - это минималистичный веб-фреймворк, для тех кто любит скорость и удобство.<br/>
        Базируется на <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a> и <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>,
        максимально раскрывая преимущества обоих технологий.
    </i>
</p>

---

## **Ключевые особенности:**

* ✏️ Минимализм - проверяйте и получайте данные всего одной строкой
* 🐍 Нативная поддержка типов python
* 📔 Полная интеграция с <a href="https://github.com/pydantic/pydantic">pydantic</a> (полная поддержка **v1** и **v2**)
* 🚀 Работает на базе <a href="https://github.com/aio-libs/aiohttp">aiohttp</a> с поддержкой нативных функций
* 📤 Удобное извлечение основных типов из входящих данных

## **Установка**

```bash
pip install rapidy
```

## **Простое приложение**

```Python
{!> ./index/ex.py !}
```

<span class="success-color">Success</span> request validation
```bash
{!> ./index/ex_success_validation.sh !}
```
```
{!> ./index/ex_success_validation_result.txt !}
```

<span class="warning-color">Failed</span> request validation
```bash
{!> ./index/ex_failure_validation.sh !}
```
```
{!> ./index/ex_failure_validation_result.txt !}
```

**Быстрый старт [Quickstart](quickstart.md)**<br/>
**Больше примеров [Examples](examples.md)**
