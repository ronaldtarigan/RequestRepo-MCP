from __future__ import annotations

from requestrepo_mcp.client import RequestrepoClientManager
from requestrepo_mcp.config import RequestrepoConfig


def test_client_manager_prefers_token_and_is_singleton() -> None:
    calls: list[dict[str, object]] = []

    def factory(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return object()

    config = RequestrepoConfig(token="tok", admin_token="adm")
    manager = RequestrepoClientManager(config, client_factory=factory)

    first = manager.get_client()
    second = manager.get_client()

    assert first is second
    assert len(calls) == 1
    assert calls[0]["token"] == "tok"
    assert "admin_token" not in calls[0]


def test_client_manager_uses_admin_token_when_no_token() -> None:
    calls: list[dict[str, object]] = []

    def factory(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return object()

    config = RequestrepoConfig(token=None, admin_token="adm")
    manager = RequestrepoClientManager(config, client_factory=factory)
    manager.get_client()

    assert calls[0]["admin_token"] == "adm"
    assert "token" not in calls[0]
