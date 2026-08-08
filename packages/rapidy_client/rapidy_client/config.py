from __future__ import annotations

import os
from collections.abc import Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, FilePath, HttpUrl
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from rapidy_client._models import Timeout


class PoolLimits(BaseModel):
    max_connections: int = 100
    max_per_host: int = 20
    keepalive_timeout: float = 15.0
    force_close: bool = False


class BackoffConfig(BaseModel):
    base: float = 0.1
    cap: float = 5.0
    jitter: Literal["full", "none"] = "full"


class RetryConfig(BaseModel):
    max_attempts: int = 3
    statuses: frozenset[int] = frozenset({429, 502, 503, 504})
    on_network_errors: bool = True
    methods: frozenset[str] = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})
    respect_retry_after: bool = True
    retry_after_cap: float = 30.0
    backoff: BackoffConfig = Field(default_factory=BackoffConfig)
    budget_ratio: float | None = 0.1


class BreakerConfig(BaseModel):
    failure_threshold: int = 5
    failure_statuses: frozenset[int] = frozenset({500, 502, 503, 504})
    recovery_time: float = 30.0
    half_open_max_calls: int = 1
    granularity: Literal["upstream", "host"] = "upstream"


class RateLimitConfig(BaseModel):
    rate: float
    burst: int = 1
    acquire_timeout: float = 5.0


class RedirectConfig(BaseModel):
    follow: bool = False
    max_redirects: int = 5
    strip_auth_on_origin_change: bool = True


class TLSConfig(BaseModel):
    verify: bool = True
    ca_file: FilePath | None = None
    client_cert: FilePath | None = None
    client_key: FilePath | None = None
    min_version: Literal["TLSv1_2", "TLSv1_3"] = "TLSv1_2"


class ProxyConfig(BaseModel):
    url: HttpUrl | None = None
    trust_env: bool = False
    no_proxy: frozenset[str] = frozenset()


class DeadlineConfig(BaseModel):
    respect_incoming: bool = True
    propagate: bool = True
    header: str = "x-rapidy-deadline-ms"


class LogConfig(BaseModel):
    level: Literal["off", "meta", "headers", "body"] = "meta"
    max_body_len: int = 2000
    redact_headers_extra: frozenset[str] = frozenset()
    redact_query_extra: frozenset[str] = frozenset()


class UpstreamConfig(BaseModel):
    base_url: HttpUrl
    timeout: Timeout = Field(default_factory=Timeout)
    limits: PoolLimits = Field(default_factory=PoolLimits)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    breaker: BreakerConfig | None = None
    bulkhead_limit: int | None = None
    rate_limit: RateLimitConfig | None = None
    redirects: RedirectConfig = Field(default_factory=RedirectConfig)
    tls: TLSConfig = Field(default_factory=TLSConfig)
    proxy: ProxyConfig | None = None
    cookies: Literal["disabled", "shared"] = "disabled"
    default_headers: dict[str, str] = Field(default_factory=dict)
    deadline: DeadlineConfig = Field(default_factory=DeadlineConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    max_response_size: int | None = None
    error_body_limit: int = 65536
    allow_absolute_urls: bool = False


class _FileSecretEnvSource(EnvSettingsSource):
    def _load_env_vars(self) -> Mapping[str, str | None]:
        raw = dict(super()._load_env_vars())
        prefix = self.env_prefix.lower()
        resolved: dict[str, str | None] = {}
        secrets: dict[str, str] = {}
        for key, value in raw.items():
            if key.startswith(prefix) and key.endswith("_file") and value:
                target = key[: -len("_file")]
                secrets[target] = Path(value).read_text(encoding="utf-8").strip()
            else:
                resolved[key] = value
        for target, secret in secrets.items():
            resolved.setdefault(target, secret)
        return resolved


class HttpSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAPIDY_CLIENT__",
        env_nested_delimiter="__",
    )

    upstreams: dict[str, UpstreamConfig] = Field(default_factory=dict)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del cls, env_settings
        return (
            init_settings,
            _FileSecretEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


rapidy_client_request_id: ContextVar[str | None] = ContextVar(
    "rapidy_client_request_id",
    default=None,
)
rapidy_client_deadline: ContextVar[float | None] = ContextVar(
    "rapidy_client_deadline",
    default=None,
)


def client_debug_enabled() -> bool:
    return os.environ.get("RAPIDY_CLIENT_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def render_effective_config(
    *,
    upstream_name: str,
    endpoint: str | None,
    timeout: Timeout,
    retry: RetryConfig | None,
    redirects: RedirectConfig,
    deadline: float | None,
) -> str:
    retry_value = None if retry is None else retry.model_dump(mode="json")
    redirects_value = redirects.model_dump(mode="json")
    return "\n".join(
        (
            f"upstream={upstream_name!r}",
            f"endpoint={endpoint!r}",
            f"timeout={timeout!r}",
            f"retry={retry_value!r}",
            f"redirects={redirects_value!r}",
            f"deadline={deadline!r}",
        )
    )


__all__ = (
    "BackoffConfig",
    "BreakerConfig",
    "DeadlineConfig",
    "HttpSettings",
    "LogConfig",
    "PoolLimits",
    "ProxyConfig",
    "RateLimitConfig",
    "RedirectConfig",
    "RetryConfig",
    "TLSConfig",
    "UpstreamConfig",
    "client_debug_enabled",
    "rapidy_client_deadline",
    "rapidy_client_request_id",
    "render_effective_config",
)
