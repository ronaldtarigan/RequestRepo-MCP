from __future__ import annotations

import anyio

from mcp.server.fastmcp import FastMCP

from requestrepo_mcp.server import create_mcp_server, main


def test_server_registers_expected_tools() -> None:
    mcp = create_mcp_server()
    tools = anyio.run(mcp.list_tools)
    tool_names = {tool.name for tool in tools}

    assert {
        "session_info",
        "list_requests",
        "wait_for_request",
        "delete_request",
        "delete_all_requests",
        "share_request",
        "get_shared_request",
        "list_dns",
        "add_dns",
        "remove_dns",
        "update_dns",
        "list_files",
        "get_file",
        "set_file",
        "update_files",
        "ping",
    }.issubset(tool_names)


def test_main_stdio_calls_mcp_run(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(self, transport: str = "stdio", **kwargs):  # type: ignore[no-untyped-def]
        calls.append((transport, kwargs))

    monkeypatch.setattr(FastMCP, "run", fake_run)
    main(["--transport", "stdio"])

    assert calls == [("stdio", {})]


def test_main_streamable_http_calls_mcp_run(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run(self, transport: str = "stdio", **kwargs):  # type: ignore[no-untyped-def]
        calls.append((transport, kwargs))

    monkeypatch.setattr(FastMCP, "run", fake_run)
    main(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--streamable-http-path",
            "/mcp",
        ]
    )

    assert calls == [("streamable-http", {})]
