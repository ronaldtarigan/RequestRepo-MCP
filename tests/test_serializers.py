from __future__ import annotations

from requestrepo import Response
from requestrepo.models import HttpRequest

from requestrepo_mcp.serializers import bytes_envelope, serialize_file_response, serialize_request


def test_bytes_envelope_handles_utf8_and_truncation() -> None:
    payload = bytes_envelope(b"hello", max_bytes=3)
    assert payload["size"] == 5
    assert payload["truncated"] is True
    assert payload["utf8"] == "hel"


def test_bytes_envelope_handles_non_utf8() -> None:
    payload = bytes_envelope(b"\xff\xfe", max_bytes=10)
    assert payload["size"] == 2
    assert payload["truncated"] is False
    assert payload["utf8"] is None


def test_serialize_request_for_http_contains_safe_bytes() -> None:
    request = HttpRequest(
        _id="req-1",
        type="http",
        raw=b"raw-body",
        uid="uid-1",
        ip="1.2.3.4",
        country="US",
        date=1_700_000_000,
        method="POST",
        path="/submit",
        http_version="HTTP/1.1",
        headers={"content-type": "application/json"},
        body=b'{"ok":true}',
    )

    payload = serialize_request(
        request,
        include_raw=True,
        include_body=True,
        max_bytes=4,
    )

    assert payload["id"] == "req-1"
    assert payload["type"] == "http"
    assert payload["date_iso"] is not None
    assert payload["raw"]["truncated"] is True
    assert payload["body"]["truncated"] is True
    assert isinstance(payload["raw"]["base64"], str)
    assert isinstance(payload["body"]["base64"], str)


def test_serialize_file_response_decodes_base64() -> None:
    response = Response(raw="aGVsbG8=", headers=[], status_code=200)
    payload = serialize_file_response(response, decode_base64=True, max_bytes=5)
    assert payload["raw_base64"] == "aGVsbG8="
    assert payload["raw_decoded"]["utf8"] == "hello"
