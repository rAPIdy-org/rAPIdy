# Changelog

All notable changes to `rapidy-client` are documented here.

## 0.1.0 — 2026-08-08

Initial standalone client release for the rAPIdy family.

### Added

- Async `HttpClient` with explicit request/response models and `httpx2`
  transport isolation.
- Deterministic middleware pipeline for correlation, deadlines, redirects,
  retries, observability, and custom middleware.
- Declarative HTTP schema with typed parameter markers, controllers,
  `bind(target, client)`, response validation, status dispatch, and `Result[T]`.
- Native `rapidy-core` component DI through `HttpApp` and endpoint/controller
  providers.
- Streaming request and response bodies, file uploads, and multipart encoding.
- Imperative and declarative WebSocket and SSE clients with reconnect and typed
  message validation.
- Testing primitives: `MockTransport`, `FakeClock`, and `ChaosServer`.
- Typed distribution metadata and `py.typed` marker.

### Quality

- Golden end-to-end traces for happy path, retry/deadline, `Result[T]`, and DI.
- Property suites for retry math, serialization, redaction, and protocol frame
  splicing.
- Lifecycle, loopback transport, distribution, performance regression, and
  streaming-memory release gates.

### Deferred

- Auth refresh, idempotency-key generation, and pagination remain v-next.
- Circuit breaker, bulkhead, and rate-limit extras remain planned for v1.1.
