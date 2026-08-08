import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from rapidy_client import (
    BackoffConfig,
    BreakerConfig,
    DeadlineConfig,
    HttpSettings,
    LogConfig,
    PoolLimits,
    ProxyConfig,
    RateLimitConfig,
    RedirectConfig,
    RetryConfig,
    Timeout,
    TLSConfig,
    UpstreamConfig,
)
from rapidy_client.config import (
    client_debug_enabled,
    rapidy_client_deadline,
    rapidy_client_request_id,
    render_effective_config,
)


def _clear_client_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.startswith("RAPIDY_CLIENT__"):
            monkeypatch.delenv(name, raising=False)


def test_pool_limits_defaults() -> None:
    limits = PoolLimits()
    assert limits.max_connections == 100
    assert limits.max_per_host == 20
    assert limits.keepalive_timeout == 15.0
    assert limits.force_close is False


def test_backoff_config_defaults() -> None:
    backoff = BackoffConfig()
    assert backoff.base == 0.1
    assert backoff.cap == 5.0
    assert backoff.jitter == "full"


def test_retry_config_defaults() -> None:
    retry = RetryConfig()
    assert retry.max_attempts == 3
    assert retry.statuses == frozenset({429, 502, 503, 504})
    assert retry.on_network_errors is True
    assert retry.methods == frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})
    assert retry.respect_retry_after is True
    assert retry.retry_after_cap == 30.0
    assert retry.backoff == BackoffConfig()
    assert retry.budget_ratio == 0.1


def test_breaker_config_defaults() -> None:
    breaker = BreakerConfig()
    assert breaker.failure_threshold == 5
    assert breaker.failure_statuses == frozenset({500, 502, 503, 504})
    assert breaker.recovery_time == 30.0
    assert breaker.half_open_max_calls == 1
    assert breaker.granularity == "upstream"


def test_rate_limit_requires_rate() -> None:
    with pytest.raises(ValidationError):
        RateLimitConfig()  # type: ignore[call-arg]
    rate_limit = RateLimitConfig(rate=10.0)
    assert rate_limit.burst == 1
    assert rate_limit.acquire_timeout == 5.0


def test_redirect_config_defaults() -> None:
    redirects = RedirectConfig()
    assert redirects.follow is False
    assert redirects.max_redirects == 5
    assert redirects.strip_auth_on_origin_change is True


def test_tls_config_defaults() -> None:
    tls = TLSConfig()
    assert tls.verify is True
    assert tls.ca_file is None
    assert tls.client_cert is None
    assert tls.client_key is None
    assert tls.min_version == "TLSv1_2"


def test_proxy_config_defaults() -> None:
    proxy = ProxyConfig()
    assert proxy.url is None
    assert proxy.trust_env is False
    assert proxy.no_proxy == frozenset()


def test_deadline_config_defaults() -> None:
    deadline = DeadlineConfig()
    assert deadline.respect_incoming is True
    assert deadline.propagate is True
    assert deadline.header == "x-rapidy-deadline-ms"


def test_log_config_defaults() -> None:
    log = LogConfig()
    assert log.level == "meta"
    assert log.max_body_len == 2000
    assert log.redact_headers_extra == frozenset()
    assert log.redact_query_extra == frozenset()


def test_upstream_config_defaults() -> None:
    config = UpstreamConfig(base_url="https://x.example.com")  # type: ignore[arg-type]
    assert config.timeout == Timeout()
    assert config.limits == PoolLimits()
    assert config.retry == RetryConfig()
    assert config.breaker is None
    assert config.bulkhead_limit is None
    assert config.rate_limit is None
    assert config.redirects == RedirectConfig()
    assert config.tls == TLSConfig()
    assert config.proxy is None
    assert config.cookies == "disabled"
    assert config.default_headers == {}
    assert config.deadline == DeadlineConfig()
    assert config.log == LogConfig()
    assert config.max_response_size is None
    assert config.error_body_limit == 65536
    assert config.allow_absolute_urls is False


def test_upstream_config_defaults_are_not_shared() -> None:
    first = UpstreamConfig(base_url="https://one.example.com")  # type: ignore[arg-type]
    second = UpstreamConfig(base_url="https://two.example.com")  # type: ignore[arg-type]
    first.default_headers["X-Test"] = "one"
    assert second.default_headers == {}


def test_upstream_config_requires_base_url() -> None:
    with pytest.raises(ValidationError):
        UpstreamConfig()  # type: ignore[call-arg]


def test_http_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_client_env(monkeypatch)
    settings = HttpSettings()
    assert settings.upstreams == {}
    assert settings.model_config["env_prefix"] == "RAPIDY_CLIENT__"
    assert settings.model_config["env_nested_delimiter"] == "__"


def test_http_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_client_env(monkeypatch)
    monkeypatch.setenv(
        "RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL",
        "https://billing.example.com",
    )
    settings = HttpSettings()
    assert str(settings.upstreams["billing"].base_url).startswith(
        "https://billing.example.com"
    )


def test_http_settings_file_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_client_env(monkeypatch)
    secret = tmp_path / "billing-url"
    secret.write_text("https://secret.example.com\n", encoding="utf-8")
    monkeypatch.setenv(
        "RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL_FILE",
        str(secret),
    )
    settings = HttpSettings()
    assert str(settings.upstreams["billing"].base_url).startswith(
        "https://secret.example.com"
    )

    monkeypatch.setenv(
        "RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL",
        "https://direct.example.com",
    )
    direct = HttpSettings()
    assert str(direct.upstreams["billing"].base_url).startswith(
        "https://direct.example.com"
    )


def test_http_settings_typo_fails_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_client_env(monkeypatch)
    monkeypatch.setenv(
        "RAPIDY_CLIENT__UPSTREAMS__BILLING__BASE_URL",
        "not-a-url",
    )
    with pytest.raises(ValidationError):
        HttpSettings()


def test_contextvars_default_none() -> None:
    assert rapidy_client_request_id.get() is None
    assert rapidy_client_deadline.get() is None


@pytest.mark.parametrize("value", ["1", " true ", "yes", "ON"])
def test_client_debug_enabled_truthy(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("RAPIDY_CLIENT_DEBUG", value)
    assert client_debug_enabled() is True
    monkeypatch.setenv("RAPIDY_CLIENT_DEBUG", "0")
    assert client_debug_enabled() is False


def test_render_effective_config_debug_repr() -> None:
    rendered = render_effective_config(
        upstream_name="billing",
        endpoint="/x/{id}",
        timeout=Timeout(total=2.5),
        retry=RetryConfig(),
        redirects=RedirectConfig(follow=True),
        deadline=None,
    )
    assert "billing" in rendered
    assert "/x/{id}" in rendered
    assert "2.5" in rendered
    assert "follow" in rendered
    assert "token" not in rendered.casefold()


def test_config_facade_reexport() -> None:
    assert HttpSettings.__module__ == "rapidy_client.config"
    assert UpstreamConfig.__module__ == "rapidy_client.config"
