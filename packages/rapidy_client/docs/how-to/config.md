# Client configuration

`UpstreamConfig` describes one upstream. It validates URLs and policy values at
startup, before a request can reach production traffic.

```python
from rapidy_client import RedirectConfig, Timeout, UpstreamConfig

catalog = UpstreamConfig(
    base_url="https://catalog.example.com",
    timeout=Timeout(total=10, connect=2, read=8),
    redirects=RedirectConfig(follow=False, max_redirects=5),
    default_headers={"Accept": "application/json"},
)
```

The composite configuration includes pool limits, retry, redirects, TLS and
mTLS, proxy, cookies, deadlines, logging, and response-size policies. TLS
verification and cookie isolation are enabled by default (`verify=True`,
`cookies="disabled"`).

`ProxyConfig.no_proxy` bypasses an explicit or environment-derived proxy for
selected destinations. A plain domain such as `example.com` matches the domain
and its subdomains; `.example.com`/`*.example.com` matches subdomains only. Exact
IPv4/IPv6 addresses, optional ports, and scheme-qualified host patterns are
supported. `*` bypasses every proxy route. Empty, path-bearing, malformed
wildcard, and CIDR entries are rejected instead of being silently ignored.

## Named upstreams from the environment

`HttpSettings` loads a registry with the `RAPIDY_CLIENT__` prefix and `__` as
the nested-field delimiter:

```shell
export RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL=https://billing.example.com
export RAPIDY_CLIENT__UPSTREAMS__BILLING__TIMEOUT__CONNECT=1.5
```

```python
from rapidy_client import HttpSettings

settings = HttpSettings()
billing = settings.upstreams["billing"]
```

Names are normalized by the settings source, so the example is available under
the `billing` key.

## File-backed values

Any variable under the client prefix can use a `_FILE` companion. The file is
read as UTF-8 and surrounding whitespace is removed:

```shell
export RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL_FILE=/run/secrets/billing_url
```

If both the direct variable and its `_FILE` form exist, the direct value wins.
A missing or unreadable file fails configuration immediately. Variables outside
the `RAPIDY_CLIENT__` namespace are not touched.

A name that already identifies a declared field ending in `_file` remains the
direct field value. In particular, `TLS__CA_FILE=/path/to/ca.pem` configures the
CA path itself and does not read the certificate text as another setting. Its
optional file-backed companion is therefore spelled `TLS__CA_FILE_FILE` and
contains the path to the CA file.

## Debug mode

Set `RAPIDY_CLIENT_DEBUG=1` (also accepts `true`, `yes`, or `on`) to enable
client debug guards and effective-configuration diagnostics. This process-wide
flag is intentionally separate from `HttpSettings` and is read dynamically.
Diagnostics include timeout/retry/redirect/deadline policies but never request
headers, tokens, or other secrets.
