# TOOLS

All tools return structured JSON.

## Safety

The following tools are destructive and require `confirm=true`:

- `delete_request`
- `delete_all_requests`
- `add_dns`
- `remove_dns`
- `update_dns`
- `set_file`
- `update_files`

## Common Output Rules

- Binary fields use envelope: `{base64, utf8, size, truncated}`
- Request timestamps include `date_unix` and `date_iso`
- Default `max_bytes` is `65536`

## Session / Requests

`session_info(include_token: bool = false)`
Use when: you need endpoint/subdomain context.
Recommendation: keep `include_token=false` unless token is explicitly needed.

`list_requests(limit: int = 100, offset: int = 0, request_type: "http"|"dns"|"smtp"|"tcp"|null = null, include_raw: bool = false, include_body: bool = false, max_bytes: int = 65536)`
Use when: you need historical requests.
Recommendation: filter by `request_type` and keep payload flags off unless needed.

`wait_for_request(request_type: "http"|"dns"|"smtp"|"tcp"|null = null, timeout_seconds: int = 30, poll_interval_seconds: float = 1.0, include_raw: bool = false, include_body: bool = false, max_bytes: int = 65536)`
Use when: you expect an incoming request soon.
Recommendation: prefer this over repeated manual polling; set explicit `timeout_seconds`.

`delete_request(request_id: str, confirm: bool)`
Use when: removing one known request.
Recommendation: verify `request_id` from `list_requests` first.

`delete_all_requests(confirm: bool)`
Use when: clearing session history.
Recommendation: avoid in shared/test-critical sessions.

`share_request(request_id: str)`
Use when: you need to share one request externally.
Recommendation: create share links only for necessary records.

`get_shared_request(share_token: str, include_raw: bool = false, include_body: bool = false, max_bytes: int = 65536)`
Use when: retrieving request data from a share token.
Recommendation: keep raw/body disabled unless debugging payload internals.

## DNS

`list_dns()`
Use when: inspecting current DNS config.

`add_dns(domain: str, record_type: "A"|"AAAA"|"CNAME"|"TXT", value: str, confirm: bool)`
Use when: appending a single record.
Recommendation: use for incremental changes.

`remove_dns(domain: str, record_type: "A"|"AAAA"|"CNAME"|"TXT"|null = null, confirm: bool)`
Use when: deleting records for a domain/type.
Recommendation: specify `record_type` when possible to reduce blast radius.

`update_dns(records: list[DnsRecordInput], confirm: bool)`
Use when: replacing the entire DNS set.
Recommendation: prefer `add_dns`/`remove_dns` unless full replacement is intended.

`DnsRecordInput = { type: "A"|"AAAA"|"CNAME"|"TXT", domain: str, value: str }`

## Files

`list_files()`
Use when: inspecting all configured response files.

`get_file(path: str, decode_base64: bool = true, max_bytes: int = 65536)`
Use when: reading one file response config.
Recommendation: keep `decode_base64=true` for quick inspection.

`set_file(path: str, body_text: str|null = null, body_base64: str|null = null, status_code: int = 200, headers: list[HeaderInput] = [], confirm: bool)`
Use when: creating/updating one file response.
Recommendation: use `body_text` for text responses, `body_base64` for binary payloads.

`update_files(files: dict[str, FileResponseInput], confirm: bool)`
Use when: replacing all file responses at once.
Recommendation: avoid unless you intend full overwrite.

`HeaderInput = { header: str, value: str }`

`FileResponseInput = { raw_base64: str, headers: HeaderInput[], status_code: int }`

## Connectivity

`ping()`
Use when: quick health check of requestrepo websocket connectivity.
