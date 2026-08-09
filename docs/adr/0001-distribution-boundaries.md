# ADR 0001: rAPIdy distribution boundaries

- Status: accepted
- Date: 2026-08-09

## Context

The repository builds three Python distributions. Splitting shared code into a
published package adds upgrade and supply-chain cost, but copying it into the
server and client would create distinct marker, sentinel, validation, and DI
types. Those identities are observable when one application uses both sides of
the family.

## Decision

Keep three distributions for the 2.0 release candidate:

- `rapidy-core` owns code that must have one runtime identity across consumers:
  `UNSET`, common enums and errors, parameter/field markers, signature
  extraction, encoding helpers, and the `rapidy_core.di` facade.
- `rapidy` owns the ASGI application, routing, server protocols, middleware,
  security, OpenAPI, testing helpers, and the `rapidy` CLI. It must not import
  `rapidy_client`.
- `rapidy-client` owns outbound HTTP, WebSocket, and SSE transports, policies,
  declarative client schemas, and client testing helpers. It must not import
  `rapidy`.

Cross-distribution imports may use only names without a leading underscore.
The cross-consumer core surface consists of `rapidy_core` plus its
`annotation_checkers`, `client_errors`, `constants`, `di`, `encoders`, `enums`,
`exceptions`, `fields`, `parameters.http`, `signature`, and `typedefs` facades.
Names beginning with an underscore remain implementation details even inside
those modules.

`rapidy-core` exposes an integer `CORE_API_VERSION`. Both consumers validate
the expected epoch during their root import. A mismatch is an `ImportError`
that names the compatible dependency range. This runtime check supplements,
but does not replace, package metadata constraints.

All three distributions have a Python 3.12 floor. For the current epoch,
`rapidy` and `rapidy-client` require `rapidy-core>=0.1,<0.2`. A backward-
compatible core patch may ship independently. An incompatible core change must:

1. increment the core minor line and `CORE_API_VERSION`;
2. update both consumers and their dependency ranges in the same repository
   change;
3. pass source, wheel, type, and import-boundary gates for all affected
   distributions before any artifact is published.

Partial upgrades are supported only when both the declared dependency range and
the API epoch match. Resolver bypasses or manually mixed incompatible artifacts
are expected to fail at import, not later during request handling.

Dishka remains a dependency of `rapidy-core` for this epoch because
`rapidy_core.di` is the single facade consumed by both server and client.
`rapidy-client` has no direct Dishka requirement. Moving DI behind an extra or
out of core requires a separate ADR and evidence that shared DI composition and
type identity are preserved.

### Public import and third-party type policy

The three root modules intentionally serve different purposes:

- `rapidy` is a frozen application facade: `Rapidy`, `run_app`, and the
  distribution version. Server features are imported from owned facades such
  as `rapidy.http`, `rapidy.security`, and `rapidy.testing`.
- `rapidy_client` is an ergonomic client facade for common runtime,
  configuration, and operation names. Parameter markers and serialization
  controls stay in `rapidy_client.schema`, where short names cannot be confused
  with server route markers.
- `rapidy_core` is primarily a consumer boundary. Application code should use
  the server or client facade; the only root identities deliberately shared
  with `rapidy_client` are `UNSET` and `Unset`.

Equal short names in server and client submodules describe their local domain;
they are not cross-distribution identity promises. Root `__all__` contracts and
the `UNSET`/`Unset` identity are regression-tested, so a new re-export requires
an explicit compatibility decision.

Third-party types are allowed only at deliberate integration boundaries.
Pydantic models and fields are part of the validation contract; the optional
server testing facade follows the HTTPX client model; multidict-backed HTTP
collections preserve their mapping behavior; and Dishka types are exposed only
through `rapidy_core.di`/consumer DI facades. Transport implementations such as
`httpx2`, `httpcore2`, and `wsproto` must not leak into client models or schema
APIs and remain enforced by import-linter contracts. Counting a supported
integration type in a public signature is not itself a defect; leaking a type
from outside these named boundaries is.

## Consequences

The split has an explicit maintenance cost: the two currently unreserved PyPI
names block release, and core compatibility must be tested as a family. In
return, shared public annotations and sentinels retain one identity without
vendored copies, and the server and client remain independently installable.

This decision is a working architecture, not a permanent commitment. Revisit it
after real adoption data exists or if the shared surface can be reduced enough
to eliminate the published core without breaking cross-package contracts.
