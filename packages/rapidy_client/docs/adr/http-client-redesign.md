# ADR: rapidy-client v1 architecture

- Status: accepted
- Scope: `rapidy-client` 0.1 / rAPIdy v1
- Last verified: 2026-08-08

## 1. Context

The former HTTP client mixed transport details, framework integration, retries,
configuration, and response parsing. That made behavior difficult to test and
made the package inseparable from the server framework.

The v1 redesign establishes `rapidy-client` as a standalone async client built
on `rapidy-core` contracts. The umbrella `rapidy` distribution may re-export the
client, but the client does not import server implementation modules.

## 2. Decision

### Package boundary

`rapidy-client` owns outbound HTTP, WebSocket, and SSE behavior. It depends on
the public DI and parameter-marker facades of `rapidy-core`. Server-specific
code and legacy transport implementations are forbidden dependencies.

The package exposes a typed `py.typed` distribution and supports Python 3.13
and 3.14.

### Request pipeline

The client builds one framework-neutral `Request` and executes it through an
onion-style middleware pipeline. Stock behavior has a deterministic order:

1. correlation and request-level observation;
2. redirect policy;
3. logical deadline propagation;
4. retry policy and retry budget;
5. per-attempt middleware;
6. transport.

Response status handling and typed response parsing occur outside the
middleware chain. Middleware therefore observes the real transport response,
not a status exception produced by a later parsing step.

### Transport boundary

`HttpxTransport` is the only HTTP transport adapter. `httpx2` and `httpcore2`
must not leak into public models or middleware. Transport exceptions are mapped
to the stable `rapidy_client.errors` hierarchy, including timeout phase and the
distinction between protocol corruption and a disconnected reused connection.

`wsproto` is localized to the WebSocket implementation. SSE parsing remains a
transport-independent byte-stream operation.

### Configuration

`UpstreamConfig` is immutable input to a client. Call-level values override
endpoint declarations, which override controller defaults, which override the
upstream configuration. Secrets may come from file-backed environment values
without becoming part of the public request model.

Timeout and deadline are separate concepts. Timeout limits an operation phase;
deadline is a logical budget shared by all attempts. Before every attempt the
remaining deadline must cover the connect timeout. When propagation is enabled,
the remaining budget is written to `x-rapidy-deadline-ms`.

### Retry semantics

Retries are permitted only for configured methods or explicitly idempotent
requests with replayable bodies. Failed response bodies are closed before the
virtual or real backoff sleep. `Retry-After` replaces exponential backoff when
valid and is capped by configuration. A process-local token budget prevents a
retry storm.

Tests use `FakeClock`; golden and property suites contain no wall-clock sleeps.

### Declarative API

Declarations are environment-free. `@get`, the other HTTP method decorators,
`@controller`, `@ws`, and `@sse` describe request shape and response type.
`bind(target, client)` performs explicit binding. Declarations do not carry an
upstream name and do not expose a stateful `.bind()` method.

Parameter markers are imported from the schema facade and remain compatible
with their `rapidy-core` definitions. Both default-value and `Annotated` forms
produce the same request.

Return annotations drive parsing. `Result[T]` preserves the parsed value,
status, and headers for successful and explicitly declared statuses. An
undeclared error status still raises `StatusError`.

### Dependency injection

DI integration is optional in usage but part of the main distribution.
`Component` qualifies multiple `HttpClient` instances of the same type.
`HttpApp` is the composition root and owns APP-scoped clients, controllers, and
functional endpoint providers. It creates the container on entry and finalizes
every client exactly once on normal and exceptional exit.

The client package imports only the `rapidy_core.di` facade; it does not import
the underlying DI implementation directly.

### Streaming and protocols

Buffered responses may be read repeatedly from their cache. An unbuffered
response stream has a single consumer. Finite streams participate in graceful
draining; WebSocket and SSE sessions are closed immediately during shutdown.

WebSocket sends are serialized through a bounded queue and may be initiated
concurrently. Receive has one active consumer. SSE reconnect preserves the
last event identifier. Both protocols validate typed messages at their public
boundary and map failures into the client error hierarchy.

### Lifecycle

The client binds lazily to the first running event loop and rejects use from a
different loop. Once closing starts, new requests and protocol sessions fail
with `ClientClosedError`. Finite requests receive a bounded drain interval;
remaining work is cancelled afterward. Externally supplied transports are not
owned or closed by the client.

### Observability and security

Observers receive request, retry, pool, and connection events. Observer failure
is isolated from the request, except cancellation, which always propagates.

Redaction is a system invariant for framework-owned URLs, headers, request and
response representations, logs, and every `HttpClientError` subclass. Arbitrary
application model representations are outside that guarantee and should use
Pydantic secret fields or `repr=False`.

## 3. Verification

The release gate combines:

- unit, contract, golden, property, lifecycle, and loopback integration tests;
- at least 90% package coverage;
- strict mypy, Ruff, and import-linter checks;
- Python 3.13 and 3.14 test runs;
- a committed multi-variant performance baseline, with `+di` as the hard gate;
- a streaming-memory ceiling of 32 MiB while consuming a logical 2 GiB body;
- wheel and sdist inspection plus public-import smoke tests.

The performance gate runs five co-located `bare_httpx2`/`no-di`/`+di` trials and
uses medians, so a single noisy runner sample cannot decide the release verdict.
The hard metric is the paired `+di` minus `no-di` overhead ratio from the same
trial; this keeps the verdict independent of whether the runner is macOS or
Ubuntu. The limit is the larger of 10 percentage points (the measured noise
floor) and 15% headroom over the committed incremental-DI baseline. Absolute
no-DI and `+di` ratios remain diagnostics and do not decide the gate.

## 4. Consequences

The architecture adds explicit models and adapters, but every layer can be
tested independently and the full stack can be exercised with `MockTransport`
or the deterministic loopback `ChaosServer`.

Auth refresh, idempotency-key generation, pagination, and resilience extras are
not part of v1. They may be added later without weakening the package boundary
or changing the declarative binding model.
