"""MCP server for requestrepo."""

from __future__ import annotations

import argparse
import base64
import binascii
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from requestrepo import DnsRecord, Header, Response

from .client import RequestrepoClientManager
from .config import RequestrepoConfig
from .schemas import DnsRecordInput, DnsRecordType, FileResponseInput, HeaderInput, RequestType
from .serializers import serialize_dns_record, serialize_file_response, serialize_request


class RequestrepoMCPService:
    """Business logic for requestrepo tool operations."""

    def __init__(
        self,
        *,
        config: RequestrepoConfig | None = None,
        client_manager: RequestrepoClientManager | None = None,
    ) -> None:
        self.config = config or RequestrepoConfig.from_env()
        self.client_manager = client_manager or RequestrepoClientManager(self.config)

    def _client(self):
        return self.client_manager.get_client()

    def _resolved_max_bytes(self, max_bytes: int | None) -> int:
        if max_bytes is None:
            return self.config.max_bytes
        if max_bytes < 1:
            raise ValueError("max_bytes must be >= 1.")
        return max_bytes

    @staticmethod
    def _require_confirm(confirm: bool, action: str) -> None:
        if not confirm:
            raise ValueError(f"{action} is destructive and requires confirm=true.")

    def session_info(self, *, include_token: bool = False) -> dict[str, Any]:
        client = self._client()
        payload: dict[str, Any] = {
            "subdomain": client.subdomain,
            "domain": client.domain,
            "endpoint": f"{client.subdomain}.{client.domain}",
        }
        if include_token:
            payload["token"] = client.token
        return payload

    def list_requests(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        request_type: RequestType | None = None,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        if limit < 1:
            raise ValueError("limit must be >= 1.")
        if offset < 0:
            raise ValueError("offset must be >= 0.")

        resolved_max_bytes = self._resolved_max_bytes(max_bytes)
        requests = self._client().list_requests(limit=limit, offset=offset)
        if request_type is not None:
            requests = [request for request in requests if request.type == request_type]

        return {
            "limit": limit,
            "offset": offset,
            "request_type": request_type,
            "count": len(requests),
            "requests": [
                serialize_request(
                    request,
                    include_raw=include_raw,
                    include_body=include_body,
                    max_bytes=resolved_max_bytes,
                )
                for request in requests
            ],
        }

    def wait_for_request(
        self,
        *,
        request_type: RequestType | None = None,
        timeout_seconds: int | None = None,
        poll_interval_seconds: float = 1.0,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0.")

        resolved_timeout = self.config.default_timeout_seconds if timeout_seconds is None else timeout_seconds
        if resolved_timeout < 0:
            raise ValueError("timeout_seconds must be >= 0.")

        resolved_max_bytes = self._resolved_max_bytes(max_bytes)
        client = self._client()
        deadline = time.monotonic() + resolved_timeout
        seen_ids = {request.id for request in client.list_requests(limit=100, offset=0)}

        while time.monotonic() <= deadline:
            requests = client.list_requests(limit=100, offset=0)
            new_requests = [request for request in requests if request.id not in seen_ids]
            seen_ids.update(request.id for request in requests)

            if request_type is not None:
                new_requests = [request for request in new_requests if request.type == request_type]

            if new_requests:
                selected = max(new_requests, key=lambda request: request.date)
                return {
                    "found": True,
                    "timeout": False,
                    "request_type": request_type,
                    "request": serialize_request(
                        selected,
                        include_raw=include_raw,
                        include_body=include_body,
                        max_bytes=resolved_max_bytes,
                    ),
                }

            sleep_for = min(poll_interval_seconds, max(0.0, deadline - time.monotonic()))
            if sleep_for <= 0:
                break
            time.sleep(sleep_for)

        return {
            "found": False,
            "timeout": True,
            "request_type": request_type,
            "request": None,
        }

    def delete_request(self, *, request_id: str, confirm: bool) -> dict[str, Any]:
        self._require_confirm(confirm, "delete_request")
        deleted = self._client().delete_request(request_id)
        return {"request_id": request_id, "deleted": deleted}

    def delete_all_requests(self, *, confirm: bool) -> dict[str, Any]:
        self._require_confirm(confirm, "delete_all_requests")
        deleted = self._client().delete_all_requests()
        return {"deleted": deleted}

    def share_request(self, *, request_id: str) -> dict[str, Any]:
        share_token = self._client().share_request(request_id)
        return {
            "request_id": request_id,
            "share_token": share_token,
            "share_url": f"{self.config.protocol}://{self.config.host}/r/{share_token}",
        }

    def get_shared_request(
        self,
        *,
        share_token: str,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        request = self._client().get_shared_request(share_token)
        return {
            "share_token": share_token,
            "request": serialize_request(
                request,
                include_raw=include_raw,
                include_body=include_body,
                max_bytes=self._resolved_max_bytes(max_bytes),
            ),
        }

    def list_dns(self) -> dict[str, Any]:
        records = self._client().dns()
        return {
            "count": len(records),
            "records": [serialize_dns_record(record) for record in records],
        }

    def add_dns(
        self,
        *,
        domain: str,
        record_type: DnsRecordType,
        value: str,
        confirm: bool,
    ) -> dict[str, Any]:
        self._require_confirm(confirm, "add_dns")
        updated = self._client().add_dns(domain=domain, record_type=record_type, value=value)
        return {
            "updated": updated,
            "record": {"type": record_type, "domain": domain, "value": value},
        }

    def remove_dns(
        self,
        *,
        domain: str,
        record_type: DnsRecordType | None = None,
        confirm: bool,
    ) -> dict[str, Any]:
        self._require_confirm(confirm, "remove_dns")
        updated = self._client().remove_dns(domain=domain, record_type=record_type)
        return {
            "updated": updated,
            "domain": domain,
            "record_type": record_type,
        }

    def update_dns(self, *, records: list[DnsRecordInput], confirm: bool) -> dict[str, Any]:
        self._require_confirm(confirm, "update_dns")
        dns_records = [DnsRecord(type=record.type, domain=record.domain, value=record.value) for record in records]
        updated = self._client().update_dns(dns_records)
        return {
            "updated": updated,
            "count": len(dns_records),
            "records": [serialize_dns_record(record) for record in dns_records],
        }

    def list_files(self) -> dict[str, Any]:
        files = self._client().files()
        return {
            "count": len(files),
            "files": {
                path: serialize_file_response(response, decode_base64=False, max_bytes=self.config.max_bytes)
                for path, response in files.items()
            },
        }

    def get_file(
        self,
        *,
        path: str,
        decode_base64: bool = True,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        response = self._client().get_file(path)
        return {
            "path": path,
            "file": serialize_file_response(
                response,
                decode_base64=decode_base64,
                max_bytes=self._resolved_max_bytes(max_bytes),
            ),
        }

    def set_file(
        self,
        *,
        path: str,
        confirm: bool,
        body_text: str | None = None,
        body_base64: str | None = None,
        status_code: int = 200,
        headers: list[HeaderInput] | None = None,
    ) -> dict[str, Any]:
        self._require_confirm(confirm, "set_file")
        if (body_text is None) == (body_base64 is None):
            raise ValueError("Provide exactly one of body_text or body_base64.")

        body: str | bytes
        if body_base64 is not None:
            try:
                body = base64.b64decode(body_base64, validate=True)
            except binascii.Error as exc:
                raise ValueError(f"body_base64 must be valid base64: {exc}") from exc
        else:
            body = body_text if body_text is not None else ""

        header_models = [Header(header=header.header, value=header.value) for header in (headers or [])]
        updated = self._client().set_file(path, body, status_code=status_code, headers=header_models)
        return {
            "updated": updated,
            "path": path,
            "status_code": status_code,
            "headers": [header.model_dump() for header in header_models],
        }

    def update_files(self, *, files: dict[str, FileResponseInput], confirm: bool) -> dict[str, Any]:
        self._require_confirm(confirm, "update_files")
        payload: dict[str, Response] = {}
        for path, file_response in files.items():
            try:
                base64.b64decode(file_response.raw_base64, validate=True)
            except binascii.Error as exc:
                raise ValueError(f"files[{path!r}].raw_base64 must be valid base64: {exc}") from exc

            payload[path] = Response(
                raw=file_response.raw_base64,
                headers=[
                    Header(header=header.header, value=header.value)
                    for header in file_response.headers
                ],
                status_code=file_response.status_code,
            )

        updated = self._client().update_files(payload)
        return {"updated": updated, "count": len(payload)}

    def ping(self) -> dict[str, Any]:
        return {"ok": self._client().ping()}


def create_mcp_server(
    service: RequestrepoMCPService | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = "/mcp",
    json_response: bool = True,
    stateless_http: bool = True,
) -> FastMCP:
    """Create and configure the MCP server."""
    resolved_service = service or RequestrepoMCPService()
    mcp = FastMCP(
        name="Requestrepo MCP",
        instructions="MCP server that exposes requestrepo operations.",
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
        json_response=json_response,
        stateless_http=stateless_http,
    )

    @mcp.tool()
    def session_info(include_token: bool = False) -> dict[str, Any]:
        """Return session info for the active requestrepo client."""
        return resolved_service.session_info(include_token=include_token)

    @mcp.tool()
    def list_requests(
        limit: int = 100,
        offset: int = 0,
        request_type: RequestType | None = None,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int = 65536,
    ) -> dict[str, Any]:
        """List captured requests with optional filtering."""
        return resolved_service.list_requests(
            limit=limit,
            offset=offset,
            request_type=request_type,
            include_raw=include_raw,
            include_body=include_body,
            max_bytes=max_bytes,
        )

    @mcp.tool()
    def wait_for_request(
        request_type: RequestType | None = None,
        timeout_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int = 65536,
    ) -> dict[str, Any]:
        """Poll for a new request until timeout."""
        return resolved_service.wait_for_request(
            request_type=request_type,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            include_raw=include_raw,
            include_body=include_body,
            max_bytes=max_bytes,
        )

    @mcp.tool()
    def delete_request(request_id: str, confirm: bool) -> dict[str, Any]:
        """Delete one request."""
        return resolved_service.delete_request(request_id=request_id, confirm=confirm)

    @mcp.tool()
    def delete_all_requests(confirm: bool) -> dict[str, Any]:
        """Delete all requests for the current session."""
        return resolved_service.delete_all_requests(confirm=confirm)

    @mcp.tool()
    def share_request(request_id: str) -> dict[str, Any]:
        """Create a share token for a request."""
        return resolved_service.share_request(request_id=request_id)

    @mcp.tool()
    def get_shared_request(
        share_token: str,
        include_raw: bool = False,
        include_body: bool = False,
        max_bytes: int = 65536,
    ) -> dict[str, Any]:
        """Resolve a shared request token."""
        return resolved_service.get_shared_request(
            share_token=share_token,
            include_raw=include_raw,
            include_body=include_body,
            max_bytes=max_bytes,
        )

    @mcp.tool()
    def list_dns() -> dict[str, Any]:
        """List DNS records."""
        return resolved_service.list_dns()

    @mcp.tool()
    def add_dns(
        domain: str,
        record_type: DnsRecordType,
        value: str,
        confirm: bool,
    ) -> dict[str, Any]:
        """Add a DNS record."""
        return resolved_service.add_dns(
            domain=domain,
            record_type=record_type,
            value=value,
            confirm=confirm,
        )

    @mcp.tool()
    def remove_dns(
        domain: str,
        record_type: DnsRecordType | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Remove DNS records by domain and optional type."""
        return resolved_service.remove_dns(domain=domain, record_type=record_type, confirm=confirm)

    @mcp.tool()
    def update_dns(records: list[DnsRecordInput], confirm: bool) -> dict[str, Any]:
        """Replace the full DNS records set."""
        return resolved_service.update_dns(records=records, confirm=confirm)

    @mcp.tool()
    def list_files() -> dict[str, Any]:
        """List all file responses."""
        return resolved_service.list_files()

    @mcp.tool()
    def get_file(path: str, decode_base64: bool = True, max_bytes: int = 65536) -> dict[str, Any]:
        """Get one file response."""
        return resolved_service.get_file(path=path, decode_base64=decode_base64, max_bytes=max_bytes)

    @mcp.tool()
    def set_file(
        path: str,
        confirm: bool,
        body_text: str | None = None,
        body_base64: str | None = None,
        status_code: int = 200,
        headers: list[HeaderInput] | None = None,
    ) -> dict[str, Any]:
        """Set one file response."""
        return resolved_service.set_file(
            path=path,
            confirm=confirm,
            body_text=body_text,
            body_base64=body_base64,
            status_code=status_code,
            headers=headers,
        )

    @mcp.tool()
    def update_files(files: dict[str, FileResponseInput], confirm: bool) -> dict[str, Any]:
        """Replace all file responses."""
        return resolved_service.update_files(files=files, confirm=confirm)

    @mcp.tool()
    def ping() -> dict[str, Any]:
        """Ping the underlying requestrepo websocket connection."""
        return resolved_service.ping()

    return mcp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run requestrepo MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to run.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for streamable-http transport.")
    parser.add_argument("--port", type=int, default=8000, help="Port for streamable-http transport.")
    parser.add_argument(
        "--streamable-http-path",
        default="/mcp",
        help="Path for streamable-http transport.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    mcp = create_mcp_server(
        host=args.host,
        port=args.port,
        streamable_http_path=args.streamable_http_path,
        json_response=True,
        stateless_http=True,
    )
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
