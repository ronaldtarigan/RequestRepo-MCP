from __future__ import annotations

import pytest

from requestrepo_mcp.config import RequestrepoConfig


def test_from_env_parses_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUESTREPO_TOKEN", "tok")
    monkeypatch.setenv("REQUESTREPO_ADMIN_TOKEN", "adm")
    monkeypatch.setenv("REQUESTREPO_HOST", "example.com")
    monkeypatch.setenv("REQUESTREPO_PORT", "8443")
    monkeypatch.setenv("REQUESTREPO_PROTOCOL", "https")
    monkeypatch.setenv("REQUESTREPO_VERIFY", "false")
    monkeypatch.setenv("REQUESTREPO_DEFAULT_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("REQUESTREPO_MAX_BYTES", "2048")

    config = RequestrepoConfig.from_env()

    assert config.token == "tok"
    assert config.admin_token == "adm"
    assert config.host == "example.com"
    assert config.port == 8443
    assert config.protocol == "https"
    assert config.verify is False
    assert config.default_timeout_seconds == 12
    assert config.max_bytes == 2048


def test_from_env_rejects_invalid_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUESTREPO_VERIFY", "sometimes")
    with pytest.raises(ValueError):
        RequestrepoConfig.from_env()
