"""Configuration for requestrepo MCP."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, ValidationError


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _parse_bool(value: str, *, key: str) -> bool:
    lowered = value.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ValueError(f"{key} must be one of {_TRUE_VALUES | _FALSE_VALUES}, got {value!r}")


class RequestrepoConfig(BaseModel):
    """Runtime configuration loaded from environment variables."""

    token: str | None = None
    admin_token: str | None = None
    host: str = "requestrepo.com"
    port: int = Field(default=443, ge=1, le=65535)
    protocol: str = "https"
    verify: bool = True
    default_timeout_seconds: int = Field(default=30, ge=0)
    max_bytes: int = Field(default=65536, ge=1)

    @classmethod
    def from_env(cls) -> "RequestrepoConfig":
        """Create config from REQUESTREPO_* environment variables."""
        env = os.environ
        data: dict[str, Any] = {
            "token": env.get("REQUESTREPO_TOKEN"),
            "admin_token": env.get("REQUESTREPO_ADMIN_TOKEN"),
            "host": env.get("REQUESTREPO_HOST", "requestrepo.com"),
            "port": int(env.get("REQUESTREPO_PORT", "443")),
            "protocol": env.get("REQUESTREPO_PROTOCOL", "https"),
            "verify": _parse_bool(env["REQUESTREPO_VERIFY"], key="REQUESTREPO_VERIFY")
            if "REQUESTREPO_VERIFY" in env
            else True,
            "default_timeout_seconds": int(env.get("REQUESTREPO_DEFAULT_TIMEOUT_SECONDS", "30")),
            "max_bytes": int(env.get("REQUESTREPO_MAX_BYTES", "65536")),
        }
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Invalid REQUESTREPO_* configuration: {exc}") from exc
