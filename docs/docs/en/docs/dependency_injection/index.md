# Dependency Injection

`Rapidy` uses the [dishka](https://dishka.readthedocs.io/en/stable/) library as its built-in Dependency Injection (DI) mechanism.

We aimed to choose a DI library aligned with the philosophy of `Rapidy`: simplicity, speed, transparency, and scalability.
`dishka` perfectly fits these principles, offering developers a powerful tool without unnecessary complexity.

`dishka` is a modern and lightweight library for asynchronous dependency injection in Python applications. It focuses on high performance, minimalism, and configuration flexibility, making it ideal for next-generation web frameworks like `Rapidy`.

Its key advantages include:

- **Native asyncio support**: full support for `async`/`await`, proper lifecycle management of dependencies.
- **Minimalist architecture**: compact core, no magic, no excessive abstractions — dependency management is transparent and predictable.
- **Invisibility to business logic**: injection via type annotations (`FromDI`).
- **Flexible scope management**: `App`, `Session`, `Request`, etc.
- **Variety of providers**: factories, objects, async functions.
- **Contextual injection**: allows passing dynamic context — e.g., for the current user.
- **Framework integration**: `aiohttp`, `FastStream`, `Rapidy`, and others.
- **Testing convenience**: providers can be easily replaced in tests, no mocks or patches needed.

!!! tip "In `Rapidy`, dishka is available out-of-the-box — no additional setup required."

## Examples of using dishka in Rapidy

### Simple dependency injection example

`Rapidy` provides a `FromDI` wrapper _(alias for `FromDishka`)_, which can be used to inject dependencies:

```python
{!> ./docs/docs/dependency_injection/simple_ex.py !}
```

What happens here:

1. **Provider definition**
   The `FooProvider` class inherits from `Provider` and defines a dependency `c` of type `int`, created per request (`Scope.REQUEST`).

2. **Request handler registration**
   The `@get('/')` decorator registers the `handler` function to handle GET requests at `/`.

3. **Injecting the dependency**
   The argument `c: FromDI[int]` indicates that `c` should be obtained from the DI container at call time.

4. **Creating the application**
   A `Rapidy` instance is created with the `handler` and the `FooProvider`.

### SQLAlchemy session example

??? example "Open example"
    ```python
    {!> ./docs/docs/dependency_injection/sa_example.py !}
    ```

## Injection methods

To inject dependencies, use `rapidy.depends.FromDI` _(or `dishka.FromDishka`)_ and `rapidy.depends.FromComponent` _(or `dishka.FromComponent`)_.

```python hl_lines="11 15"
{!> ./docs/docs/dependency_injection/use_from_di.py !}
```

```python hl_lines="13 17"
{!> ./docs/docs/dependency_injection/use_from_component.py !}
```

## Features

### Accessing the container

You can access the current async container via the root `Rapidy` application. In child apps, it will be `None`.

```python
{!> ./docs/docs/dependency_injection/get_di_container.py !}
```

### Handlers and middleware

`dishka` is fully integrated with `Rapidy`, supporting auto-injection in all handler types:

```python
# providers.py
{!> ./docs/docs/dependency_injection/handlers/providers.py !}
```

**Controllers:**

```python
{!> ./docs/docs/dependency_injection/handlers/controller.py !}
```

**View classes:**

```python
{!> ./docs/docs/dependency_injection/handlers/view.py !}
```

**Middleware:**

```python
{!> ./docs/docs/dependency_injection/handlers/middleware.py !}
```

### Additional notes

- If the first handler argument lacks an annotation, `Rapidy` skips it and continues injection.
- All `dishka` features are supported: factories, nested providers, lifecycle control, and explicit dependency retrieval.

### External container

You can manually pass your own `AsyncContainer` — useful if the container is pre-created and reused across contexts.

```python
{!> ./docs/docs/dependency_injection/external_container.py !}
```

In this case:

- `Rapidy` won’t create a container.
- All `di_*` parameters are ignored.
- You must manually close the container.

## dishka limitations

`dishka` only works with HTTP handlers and middleware. If you use a container in both `faststream` and `rapidy`, you’ll need to use `@inject` explicitly in `faststream`.

## Rapidy (Application) DI attributes

##### di_container

External dependency container.

```python
di_container: AsyncContainer | None = None
```

!!! note "If `di_container` is provided, a new container won’t be created."

!!! tip "Dishka docs — [container](https://dishka.readthedocs.io/en/stable/container/index.html)."

---

##### di_providers

List of providers to register.

```python
di_providers: Sequence[BaseProvider] = ()
```

!!! note "Ignored if `di_container` is provided."

!!! tip "Dishka docs — [providers](https://dishka.readthedocs.io/en/stable/provider/index.html)."

---

##### di_scopes

Scope class.

```python
di_scopes: type[BaseScope] = Scope
```

!!! tip "Dishka docs — [scopes](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_context

Additional context for providers.

```python
di_context: dict[Any, Any] | None = None
```

!!! tip "Dishka docs — [context](https://dishka.readthedocs.io/en/stable/advanced/context.html)."

---

##### di_lock_factory

Factory for container locks.

```python
di_lock_factory: Callable[[], contextlib.AbstractAsyncContextManager[Any]] | None = Lock
```

!!! tip "Dishka docs — [lock_factory](https://dishka.readthedocs.io/en/stable/container/index.html)."

```python
{!> ./docs/docs/server/application/di_lock_factory.py !}
```

---

##### di_skip_validation

Flag to disable provider type checks.

```python
di_skip_validation: bool = False
```

!!! tip "Dishka docs — [skip_validation](https://dishka.readthedocs.io/en/stable/advanced/components.html)."

---

##### di_start_scope

Initial container scope.

```python
di_start_scope: BaseScope | None = None
```

!!! tip "Dishka docs — [start_scope](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_validation_settings

Container validation settings.

```python
di_validation_settings: ValidationSettings = DEFAULT_VALIDATION
```

!!! tip "Dishka docs — [alias](https://dishka.readthedocs.io/en/latest/provider/alias.html)."
!!! tip "Dishka docs — [from_context](https://dishka.readthedocs.io/en/latest/provider/from_context.html)."
!!! tip "Dishka docs — [provide](https://dishka.readthedocs.io/en/latest/provider/provide.html)."
