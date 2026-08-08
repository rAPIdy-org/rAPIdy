# ADR 0001: Канонический порядок middleware

## Status

Accepted для фазы Ф0, milestone 08. Решение реализует контракт §2.5 и §2.6
спецификации HTTP-клиента.

## Context

Pipeline собирается один раз в `HttpClient.__init__`, после чего его состав не
меняется. Per-request вариативность передаётся через `RequestExtensions`, а
middleware из последующих milestones наполняют предзаданные слоты, не меняя их
относительный порядок.

Порядок является частью публичного поведения: он определяет, что считается
логическим вызовом, попыткой и redirect-hop, а также какие лимиты уже заняты в
момент ошибки или повторной попытки.

## Decision

Канонический порядок снаружи внутрь:

```text
observers.on_request_start                 (вне pipeline)
→ Correlation
→ пользовательские middlewares
→ DeclaredMiddlewaresSlot                  (контроллерные → метода)
→ CircuitBreaker                           [v-next; pass-through в v1]
→ RateLimit                                [v-next; pass-through в v1]
→ Bulkhead                                 [v-next; pass-through в v1]
→ Retry
    → Auth                                 [v-next; pass-through в v1]
    → per_attempt_middlewares              (пусто по умолчанию в v1)
    → TraceContext                         [v-next; pass-through в v1]
    → Deadline
    → TotalTimeout                         (общий total попытки)
    → Redirect
    → per-hop connect/read/write/pool timeout
    → BaseTransport
observers.on_request_end/on_request_error   (вне pipeline)
raise_for_status и parsing                  (вне pipeline)
```

Отсутствующий слот — прозрачный pass-through. `retry=None` означает одну
попытку, а не отсутствие per-attempt под-цепочки.

## Rationale

- Breaker находится снаружи retry и снаружи rate-limit/bulkhead: повторные попытки не обходят fail-fast и не выжигают токены или semaphore-слоты при открытом breaker.
- Breaker получает attempt-level outcomes через механизм попыток и считает попытки, а не только логические вызовы.
- Auth находится внутри retry: каждая попытка сможет получить свежий токен после refresh на 401; в v1 слот остаётся пустым.
- Deadline расположен почти у внутреннего края pipeline, но включает ожидание внешних очередей и retry-backoff в общий бюджет.
- Redirect — самый внутренний middleware-слот: все hops наследуют контекст попытки, а внешний `TotalTimeout` ограничивает их общим остатком времени.
- Фазовые connect/read/write/pool limits остаются per-hop и применяются внутри redirect на границе транспорта.

## Consequences

Middleware milestones 10, 11 и 13, а позднее v-next 14 и 20, обязаны
активировать существующие параметры `build_pipeline`, а не переставлять слои.
Тест порядка со шпионами служит регрессионным контрактом.

V-next слоты `Auth`, `TraceContext`, `CircuitBreaker`, `RateLimit`, `Bulkhead` и
пользовательский `per_attempt_middlewares` сохраняют позиции, но по умолчанию
прозрачны в v1.

## Status handling is outside the pipeline

`raise_for_status` и parsing выполняются после выхода из pipeline. Middleware
всегда получают обычный `Response`, включая ответы 4xx и 5xx, и не создают
`StatusError` самостоятельно.
