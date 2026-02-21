"""Input schemas for MCP tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RequestType = Literal["http", "dns", "smtp", "tcp"]
DnsRecordType = Literal["A", "AAAA", "CNAME", "TXT"]


class DnsRecordInput(BaseModel):
    """DNS record payload for update_dns."""

    type: DnsRecordType
    domain: str
    value: str


class HeaderInput(BaseModel):
    """HTTP header payload for file responses."""

    header: str
    value: str


class FileResponseInput(BaseModel):
    """File response payload for update_files."""

    raw_base64: str
    headers: list[HeaderInput] = Field(default_factory=list)
    status_code: int = Field(default=200, ge=100, le=599)
