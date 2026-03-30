# Changelog — improve/googleapis-drive-v3

## Pass 2 — field_types
- Fixed: ALL endpoints (45 response definitions) — Changed response content type from `*/*` to `application/json`. The real Google Drive API returns `Content-Type: application/json; charset=UTF-8` for all JSON responses. Using `*/*` caused Prism mock server to fail with `NO_COMPLEX_OBJECT_TEXT` (HTTP 500) on every endpoint, making the mock server non-functional. Changed across all 58 paths covering 45 response content definitions.

## Pass 1 — field_presence
- Fixed: drive.about.get — Added `fields` query parameter with `required: true` to the `GET /about` operation. The real Google Drive API returns HTTP 400 with "The 'fields' parameter is required for this method." when `fields` is omitted. The shared parameter in `components/parameters` correctly defines `fields` as optional for all other endpoints, but this operation requires an explicit override at the operation level.
