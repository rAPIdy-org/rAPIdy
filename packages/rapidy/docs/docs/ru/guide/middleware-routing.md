# Middleware и mounts

Middleware образуют onion в порядке регистрации: первый — внешний. Middleware получает `Request` и `call_next`,
может валидировать Header/Cookie/Path/Query/Body, вернуть ответ без вызова хендлера или изменить готовый `Response`.

Декоратор `@middleware` принимает те же `response_*` настройки, что и HTTP-хендлер: status/content type,
валидацию, aliases, include/exclude, headers и cookies.

`HTTPRouter('/api', handlers, ...)` создаёт вложенное приложение со своими middleware, `client_max_size`, lifecycle-
хуками и lifespan. Роутеры можно вкладывать рекурсивно; DI-контейнер остаётся корневым. Регистрацию следует закончить
до startup, после него таблица роутов заморожена.

Рабочий пример middleware + mount:
[`examples/middleware_mounts.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/middleware_mounts.py).
