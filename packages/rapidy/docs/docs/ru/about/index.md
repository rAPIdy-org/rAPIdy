---
hide:
  - navigation
---

<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Историческая документация rAPIdy 1.x.** Страница сохранена только для справки и может описывать aiohttp API, которых нет в rAPIdy 2.0. Для нового кода используйте [актуальную документацию 2.0](https://rapidy.dev/).


# О компании
Добро пожаловать в раздел «О компании»! Здесь вы найдете информацию об организации Rapidy.

## О проекте
### Владелец
Меня зовут Daniil Grois **<a href="https://github.com/daniil-grois" target="_blank">@daniil-grois</a>**,
и я являюсь создателем, владельцем и ведущим разработчиком **Rapidy**.

Благодарю вас за интерес к проекту! Надеюсь, **Rapidy** поможет вам в создании собственных решений.

Буду рад вашим предложениям и доработкам — открывайте **Pull Requests**, и я сделаю все возможное, чтобы ваши идеи стали
частью **Rapidy**.

Давайте вместе делать мир лучше! 🚀

### Поддержка и развитие
Текущий состав руководителей проекта **Rapidy**:

- Daniil Grois - **<a href="https://github.com/daniil-grois" target="_blank">@daniil-grois</a>**
- Lev Zaplatin - **<a href="https://github.com/LevZaplatin" target="_blank">@LevZaplatin</a>**
- Nikita Tolstoy - **<a href="https://github.com/Nikita-Tolstoy" target="_blank">@Nikita-Tolstoy</a>**

Руководители определяют стратегию развития, приоритеты доработок и формируют **roadmap** проекта.

## Нумерация версий
**Rapidy** поддерживает **<a href="https://semver.org/" target="_blank">Semantic Versioning standard</a>**.

```
Формат версии: MAJOR.MINOR.PATCH

MAJOR – увеличение при несовместимых изменениях API
MINOR – добавление новых функций, совместимых с предыдущими версиями
PATCH – исправление ошибок без изменения API
Дополнительные метки доступны для предрелизных и сборочных версий.
```

## Как внести вклад
Хотите помочь **Rapidy** стать лучше? Вот как вы можете это сделать!

### Рабочий процесс
1. Выполните <a href="https://github.com/rapidy-org/rapidy/fork" target="_blank">fork</a> репозитория **Rapidy**.
2. Склонируйте ваш fork локально используя `git`.
   ```sh
   git clone https://github.com/your-username/rapidy.git
   ```
3. (Опционально) Установите Poetry, если он ещё не установлен:
    ```sh
    pipx install poetry
    ```
    Подробнее об установке читайте в [документации Poetry](https://python-poetry.org/docs/#installation).
4. Перейдите в папку репозитория.
5. Настройте окружение:
    ```sh
    poetry env use python3.9
    ```
6. Установите зависимости:
    ```sh
    poetry install --with dev,test,docs
    ```
7. Установите pre-commit хуки:
    ```sh
    pre-commit install
    ```
8. Активируйте виртуальное окружение:
   ```sh
   poetry shell
   ```
9. Запустите тесты, чтобы убедится, что все зависимости были установлены:
   ```sh
   pytest
   ```
10. Создайте новую ветку. Все ветки должны начинаться с префикса `<префикс>/`, обозначающего группу изменений.
Например: `bug/fix-any` / `feature/my-awesome-feature`.
11. Внесите изменения в код.
12. Напишите тесты для новых изменений.
13. Запустите линтеры и форматирование кода.
   ```sh
   pre-commit run --all-files
   ```
14. Сделайте коммит в формате `<номер ветки>: <описание>`:
   ```sh
   git commit -m "<номер ветки>: <описание>"
   ```
15. Отправьте изменения в ваш `fork`:
   ```sh
   git push
   ```
16. Откройте Pull Request <a href="https://github.com/rAPIdy-org/rAPIdy/issues/new" target="_blank">здесь</a>,
добавив понятное описание изменений в формате `<номер ветки>: <описание запроса>`.

### Code style
1. Код должен быть полностью типизирован.
2. Все изменения должны сопровождаться тестами.
3. Код должен соответствовать **PEP 8**.
4. Обратная совместимость должна сохраняться, если это возможно.
5. Внесите себя в `CONTRIBUTORS.md`.
6. Внесите изменения в документацию _(при необходимости)_.

### Discussion links
- <a href="https://t.me/+PsAvQnlVIcJlOGU6" target="_blank">telegram (en)</a>
