from __future__ import annotations

from typing import Any

import pytest
from requestrepo import DnsRecord, Header, Response
from requestrepo.models import DnsRequest, HttpRequest

from requestrepo_mcp.config import RequestrepoConfig
from requestrepo_mcp.schemas import DnsRecordInput, FileResponseInput, HeaderInput
from requestrepo_mcp.server import RequestrepoMCPService


class FakeClient:
    def __init__(self) -> None:
        self.subdomain = "abc123"
        self.domain = "requestrepo.test"
        self.token = "jwt-token"

        self.list_sequences: list[list[Any]] = []
        self.list_call_count = 0

        self.deleted_request_id: str | None = None
        self.delete_all_called = False
        self.add_dns_args: tuple[str, str, str] | None = None
        self.remove_dns_args: tuple[str, str | None] | None = None
        self.updated_dns: list[DnsRecord] | None = None
        self.updated_files: dict[str, Response] | None = None
        self.set_file_args: dict[str, Any] | None = None

    def list_requests(self, limit: int = 100, offset: int = 0) -> list[Any]:
        if self.list_sequences:
            index = min(self.list_call_count, len(self.list_sequences) - 1)
            self.list_call_count += 1
            return self.list_sequences[index]
        return []

    def delete_request(self, request_id: str) -> bool:
        self.deleted_request_id = request_id
        return True

    def delete_all_requests(self) -> bool:
        self.delete_all_called = True
        return True

    def share_request(self, request_id: str) -> str:
        return f"share-{request_id}"

    def get_shared_request(self, share_token: str) -> DnsRequest:
        return DnsRequest(
            _id="shared-1",
            type="dns",
            raw=b"abc",
            uid="uid-1",
            ip="8.8.8.8",
            country="US",
            port=53100,
            date=1_700_000_100,
            query_type="A",
            domain="example.com",
            reply="1.2.3.4",
        )

    def dns(self) -> list[DnsRecord]:
        return [DnsRecord(type="A", domain="@", value="1.2.3.4")]

    def add_dns(self, domain: str, record_type: str, value: str) -> bool:
        self.add_dns_args = (domain, record_type, value)
        return True

    def remove_dns(self, domain: str, record_type: str | None = None) -> bool:
        self.remove_dns_args = (domain, record_type)
        return True

    def update_dns(self, dns_records: list[DnsRecord]) -> bool:
        self.updated_dns = dns_records
        return True

    def files(self) -> dict[str, Response]:
        return {
            "index.html": Response(
                raw="aGVsbG8=",
                headers=[Header(header="Content-Type", value="text/plain")],
                status_code=200,
            )
        }

    def get_file(self, path: str) -> Response:
        return Response(
            raw="aGVsbG8=",
            headers=[Header(header="Content-Type", value="text/plain")],
            status_code=201,
        )

    def set_file(self, path: str, body: str | bytes, status_code: int, headers: list[Header]) -> bool:
        self.set_file_args = {
            "path": path,
            "body": body,
            "status_code": status_code,
            "headers": headers,
        }
        return True

    def update_files(self, files: dict[str, Response]) -> bool:
        self.updated_files = files
        return True

    def ping(self) -> bool:
        return True


class FakeManager:
    def __init__(self, client: FakeClient) -> None:
        self.client = client

    def get_client(self) -> FakeClient:
        return self.client


def make_service(client: FakeClient) -> RequestrepoMCPService:
    config = RequestrepoConfig(
        token="tok",
        host="requestrepo.test",
        protocol="https",
        verify=True,
        default_timeout_seconds=30,
        max_bytes=65536,
    )
    return RequestrepoMCPService(config=config, client_manager=FakeManager(client))


def _http_request(request_id: str, date: int) -> HttpRequest:
    return HttpRequest(
        _id=request_id,
        type="http",
        raw=b"raw",
        uid="uid-1",
        ip="1.1.1.1",
        country="US",
        date=date,
        method="GET",
        path="/",
        http_version="HTTP/1.1",
        headers={"accept": "*/*"},
        body=b"",
    )


def _dns_request(request_id: str, date: int) -> DnsRequest:
    return DnsRequest(
        _id=request_id,
        type="dns",
        raw=b"dns",
        uid="uid-1",
        ip="1.1.1.1",
        country="US",
        port=53000,
        date=date,
        query_type="A",
        domain="example.com",
        reply="1.2.3.4",
    )


def test_confirm_gate_blocks_destructive_action() -> None:
    service = make_service(FakeClient())
    with pytest.raises(ValueError):
        service.delete_request(request_id="req-1", confirm=False)


def test_set_file_rejects_invalid_body_combinations() -> None:
    service = make_service(FakeClient())
    with pytest.raises(ValueError):
        service.set_file(path="index.html", confirm=True)
    with pytest.raises(ValueError):
        service.set_file(
            path="index.html",
            confirm=True,
            body_text="hello",
            body_base64="aGVsbG8=",
        )


def test_set_file_accepts_base64_and_preserves_headers() -> None:
    client = FakeClient()
    service = make_service(client)
    result = service.set_file(
        path="index.html",
        confirm=True,
        body_base64="aGVsbG8=",
        status_code=201,
        headers=[HeaderInput(header="Content-Type", value="text/plain")],
    )

    assert result["updated"] is True
    assert client.set_file_args is not None
    assert client.set_file_args["body"] == b"hello"
    assert client.set_file_args["status_code"] == 201
    assert client.set_file_args["headers"][0].header == "Content-Type"


def test_wait_for_request_returns_new_matching_request() -> None:
    old_request = _http_request("old", 1_700_000_000)
    new_request = _dns_request("new", 1_700_000_005)
    client = FakeClient()
    client.list_sequences = [[old_request], [old_request, new_request]]

    service = make_service(client)
    result = service.wait_for_request(
        request_type="dns",
        timeout_seconds=1,
        poll_interval_seconds=0.01,
    )

    assert result["found"] is True
    assert result["timeout"] is False
    assert result["request"]["id"] == "new"
    assert result["request"]["type"] == "dns"


def test_wait_for_request_times_out_when_no_new_request() -> None:
    old_request = _http_request("old", 1_700_000_000)
    client = FakeClient()
    client.list_sequences = [[old_request], [old_request]]
    service = make_service(client)

    result = service.wait_for_request(
        request_type="dns",
        timeout_seconds=0,
        poll_interval_seconds=0.01,
    )

    assert result["found"] is False
    assert result["timeout"] is True


def test_dns_root_domain_preserved_and_files_round_trip_shape() -> None:
    client = FakeClient()
    service = make_service(client)

    update_result = service.update_dns(
        records=[DnsRecordInput(type="A", domain="@", value="1.2.3.4")],
        confirm=True,
    )
    assert update_result["updated"] is True
    assert client.updated_dns is not None
    assert client.updated_dns[0].domain == "@"

    files_result = service.update_files(
        files={
            "index.html": FileResponseInput(
                raw_base64="aGVsbG8=",
                status_code=202,
                headers=[HeaderInput(header="Content-Type", value="text/plain")],
            )
        },
        confirm=True,
    )
    assert files_result["updated"] is True
    assert client.updated_files is not None
    assert client.updated_files["index.html"].raw == "aGVsbG8="
    assert client.updated_files["index.html"].status_code == 202
    assert client.updated_files["index.html"].headers[0].header == "Content-Type"
