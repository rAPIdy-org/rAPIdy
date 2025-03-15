# lifespan

## Описание

**Lifespan** — это менеджер жизненного цикла фоновых задач в `Rapidy`.

Он управляет задачами, которые должны быть запущены до или после старта сервера, либо выполняться постоянно.

## on_startup

**on_startup** — это задачи, которые запускаются в цикле событий сразу после старта приложения вместе с обработчиком запросов.

!!! info "Обработчики `on_startup` должны иметь следующую сигнатуру."

    ```python
    {!> ./docs/docs/lifespan/01_on_startup/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/01_on_startup/02_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/01_on_startup/03_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/01_on_startup/04_example.py !}
    ```

    !!! note "Если у обработчика есть атрибуты, первым всегда будет передаваться текущий экземпляр `Rapidy`."

!!! example "Добавление обработчиков в уже созданный объект `Rapidy`."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/01_on_startup/05_add_example.py !}
    ```

---

## on_shutdown

**on_shutdown** — это задачи, выполняемые после остановки сервера.

Этот механизм можно использовать для корректного завершения долгоживущих соединений, таких как веб-сокеты или потоковая передача данных.

!!! info "Обработчики `on_shutdown` должны иметь следующую сигнатуру."

    ```python
    {!> ./docs/docs/lifespan/02_on_shutdown/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/02_on_shutdown/02_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/02_on_shutdown/03_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/02_on_shutdown/04_example.py !}
    ```

    !!! note "Если у обработчика есть атрибуты, первым всегда будет передаваться текущий экземпляр `Application`."

!!! example "Добавление обработчиков в уже созданный объект `Application`."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/02_on_shutdown/05_add_example.py !}
    ```

---

## on_cleanup

**on_cleanup** — это задачи, запускаемые после остановки сервера и выполнения всех `on_shutdown` обработчиков.

Этот сигнал можно использовать, например, для корректного закрытия соединений с базой данных.

!!! info "Обработчики `on_cleanup` должны иметь следующую сигнатуру."

    ```python
    {!> ./docs/docs/lifespan/03_on_cleanup/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/03_on_cleanup/02_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/03_on_cleanup/03_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/03_on_cleanup/04_example.py !}
    ```

    !!! note "Если у обработчика есть атрибуты, первым всегда будет передаваться текущий экземпляр `Application`."

!!! example "Добавление обработчиков в уже созданный объект `Application`."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/03_on_cleanup/05_add_example.py !}
    ```

!!! info "Сигналы `on_cleanup` выполняются последними."

---

## lifespan

**lifespan** отвечает за управление фоновыми задачами.

Этот механизм полезен при работе с долгоживущими задачами или в случаях, когда необходимо поддерживать определённый объект контекста, например соединения.

!!! info "Обработчики `lifespan` должны иметь следующую сигнатуру."

    ```python
    {!> ./docs/docs/lifespan/04_lifespan/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/04_lifespan/02_example.py !}
    ```

!!! example "Добавление обработчиков в уже созданный объект `Application`."

    ```python hl_lines="15"
    {!> ./docs/docs/lifespan/04_lifespan/03_add_example.py !}
    ```

!!! warning "Задачи `lifespan` завершаются перед выполнением обработчиков `on_cleanup`."
