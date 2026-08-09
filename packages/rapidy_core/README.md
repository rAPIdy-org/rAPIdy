# rapidy-core

`rapidy-core` owns the shared runtime identities used by the rAPIdy server and
client distributions: parameter markers, `UNSET`, validation primitives, and
the DI facade. It is installed as a dependency; application code should
normally depend on `rapidy` or `rapidy-client` instead.

The package is pre-1.0, but published releases still follow the compatibility
rules in the repository's distribution-boundaries ADR. Consumers validate the
core API epoch during import so an unsupported partial upgrade fails clearly.
