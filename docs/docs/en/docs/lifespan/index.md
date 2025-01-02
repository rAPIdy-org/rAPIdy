# lifespan

## Description

**Lifespan** is a lifecycle manager for background tasks in `Rapidy`.

It manages tasks that should be started before or after the server starts or run continuously.

## on_startup

**on_startup** refers to tasks that are executed in the event loop immediately after the application starts, along with the request handler.

!!! info "`on_startup` handlers must have the following signature."

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

    !!! note "If a handler has attributes, the current instance of `Rapidy` will always be passed as the first argument."

!!! example "Adding handlers to an already created `Rapidy` instance."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/01_on_startup/05_add_example.py !}
    ```

---

## on_shutdown

**on_shutdown** refers to tasks executed after the server stops.

This mechanism can be used to properly close long-lived connections such as WebSockets or streaming data.

!!! info "`on_shutdown` handlers must have the following signature."

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

    !!! note "If a handler has attributes, the current instance of `Application` will always be passed as the first argument."

!!! example "Adding handlers to an already created `Application` instance."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/02_on_shutdown/05_add_example.py !}
    ```

---

## on_cleanup

**on_cleanup** refers to tasks executed after the server stops and all `on_shutdown` handlers have been completed.

This signal can be used, for example, to properly close database connections.

!!! info "`on_cleanup` handlers must have the following signature."

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

    !!! note "If a handler has attributes, the current instance of `Application` will always be passed as the first argument."

!!! example "Adding handlers to an already created `Application` instance."

    ```python hl_lines="7"
    {!> ./docs/docs/lifespan/03_on_cleanup/05_add_example.py !}
    ```

!!! info "`on_cleanup` signals are executed last."

---

## lifespan

**lifespan** is responsible for managing background tasks.

This mechanism is useful when working with long-running tasks or when it is necessary to maintain a specific context object, such as connections.

!!! info "`lifespan` handlers must have the following signature."

    ```python
    {!> ./docs/docs/lifespan/04_lifespan/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/lifespan/04_lifespan/02_example.py !}
    ```

!!! example "Adding handlers to an already created `Application` instance."

    ```python hl_lines="15"
    {!> ./docs/docs/lifespan/04_lifespan/03_add_example.py !}
    ```

!!! warning "`lifespan` tasks complete before `on_cleanup` handlers are executed."
