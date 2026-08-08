# ADR 0002: httpcore2 trace и измерение ожидания пула

## Status

Accepted для фазы Ф1, milestone 10. Spike выполнен на `httpcore2 2.9.1`,
зафиксированном workspace lock-файлом.

## Context

Клиенту нужны признаки открытия/повторного использования соединения и время
ожидания пула. `HttpxTransport` получает асинхронный callback через request
extension `trace`, но стабильность и полнота httpcore2 trace API нужно было
проверить до добавления observer hooks.

## Findings

В `httpcore2 2.9.1` extension обрабатывает пары событий `*.started`,
`*.complete` и `*.failed`. Для соединения доступны, в частности:

- `connection.connect_tcp.*` и `connection.start_tls.*`;
- `http11.send_request_headers.*` и `http2.send_request_headers.*`;
- события отправки/получения body и закрытия response.

Начало TCP connect надёжно означает новое соединение. Если отправка заголовков
началась без connect-события в рамках запроса, транспорт может вывести признак
reuse. Отдельного события `connection_reused` нет, поэтому это именно вывод, а
не прямое значение API.

Внутренняя очередь `AsyncConnectionPool` ждёт
`pool_request.wait_for_connection()`, но это ожидание не обёрнуто trace-событием.
Следовательно, extension не даёт точной границы native pool acquire и не может
непосредственно измерить pool wait. Сам callback берётся из словаря request
extensions и реализован во внутреннем модуле `_trace.py`; набор имён не является
отдельным версионированным публичным контрактом.

## Decision

Сохраняем trace-мост `_TraceState` как основной источник connect/reuse-сигнала.
Для pool wait гарантирован fallback: собственные таймстемпы вокруг client-level
`sem.acquire()` в `HttpxTransport.handle()`. Этот fallback измеряет очередь
`max_per_host`; скрытое ожидание внутри native pool отдельно не различается.

Источник trace не блокирует Ф1. Неизвестное значение остаётся `None`, а код не
должен зависеть от конкретного набора событий для корректности запросов.

## Consequences

Milestone 11 может строить `on_pool_wait` и `on_connection_open` поверх
`_TraceState`, сохраняя nullable-семантику и fallback. При обновлении
`httpcore2` trace-события проверяются интеграционным тестом; исчезновение события
не должно ломать транспорт.
