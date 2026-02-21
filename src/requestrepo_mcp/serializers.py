"""Serialization helpers for requestrepo models."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any

from requestrepo import DnsRecord, Header, Response
from requestrepo.models import DnsRequest, HttpRequest, SmtpRequest, TcpRequest


def _iso_from_unix(ts: int | None) -> str | None:
    if ts is None:
        return None
    try:
        iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None
    return iso.replace("+00:00", "Z")


def bytes_envelope(data: bytes, max_bytes: int) -> dict[str, Any]:
    """Make bytes JSON-safe."""
    preview = data[:max_bytes]
    truncated = len(data) > max_bytes
    try:
        utf8_value: str | None = preview.decode("utf-8")
    except UnicodeDecodeError:
        utf8_value = None
    return {
        "base64": base64.b64encode(preview).decode("utf-8"),
        "utf8": utf8_value,
        "size": len(data),
        "truncated": truncated,
    }


def serialize_dns_record(record: DnsRecord) -> dict[str, str]:
    return {
        "type": record.type,
        "domain": record.domain,
        "value": record.value,
    }


def serialize_header(header: Header) -> dict[str, str]:
    return {"header": header.header, "value": header.value}


def serialize_file_response(
    response: Response,
    *,
    decode_base64: bool,
    max_bytes: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "raw_base64": response.raw,
        "headers": [serialize_header(header) for header in response.headers],
        "status_code": response.status_code,
    }
    if decode_base64:
        try:
            decoded = base64.b64decode(response.raw, validate=True)
        except binascii.Error as exc:
            payload["raw_decoded"] = None
            payload["decode_error"] = str(exc)
        else:
            payload["raw_decoded"] = bytes_envelope(decoded, max_bytes=max_bytes)
    return payload


def serialize_request(
    request: HttpRequest | DnsRequest | SmtpRequest | TcpRequest,
    *,
    include_raw: bool,
    include_body: bool,
    max_bytes: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": request.id,
        "type": request.type,
        "uid": request.uid,
        "ip": request.ip,
        "country": request.country,
        "date_unix": request.date,
        "date_iso": _iso_from_unix(request.date),
    }

    if isinstance(request, HttpRequest):
        payload.update(
            {
                "method": request.method,
                "path": request.path,
                "http_version": request.http_version,
                "headers": request.headers,
            }
        )
        if include_body and request.body is not None:
            payload["body"] = bytes_envelope(request.body, max_bytes=max_bytes)
    elif isinstance(request, DnsRequest):
        payload.update(
            {
                "port": request.port,
                "query_type": request.query_type,
                "domain": request.domain,
                "reply": request.reply,
            }
        )
    elif isinstance(request, SmtpRequest):
        payload.update(
            {
                "command": request.command,
                "data": request.data,
                "subject": request.subject,
                "from_addr": request.from_addr,
                "to": request.to,
                "cc": request.cc,
                "bcc": request.bcc,
            }
        )
    elif isinstance(request, TcpRequest):
        payload.update({"port": request.port})

    if include_raw:
        payload["raw"] = bytes_envelope(request.raw, max_bytes=max_bytes)

    return payload
