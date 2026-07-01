<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for the RIFE Frame Interpolation Pipeline.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4, region-derived endpoint
- **Client -> B2**: Short-lived presigned URLs for playback/download (10-min expiry)

## Upload Validation (source clips)

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against the **video** allowlist (MP4/MOV/WebM/MKV/AVI)
- Chunked streaming with size enforcement (500MB default)
- Empty file rejection

## Large files & long jobs

- Render output is large (the write-amplification payload) and is uploaded via boto3's
  **managed multipart transfer** (`object_store.multipart_upload_file`) — no unbounded
  in-memory buffering of the render.
- Interpolation runs in a **background thread**; failures are captured on the job manifest
  (`status=failed`, actionable `error`) rather than crashing the request. See RELIABILITY.md.

## Presigned playback URLs

- Renders and source clips are served to the `<video>` element via short-lived presigned URLs
  (10-min expiry), so no object is made public to stream it.

## Prefix-scoped deletes

- A job delete is scoped strictly to `renders/<clip_id>/<multiplier>x/`
  (`object_store.delete_prefix` refuses an empty/root/bare `renders/` prefix), so a delete
  can never wipe another job's renders or a shared bucket.

## File Key Validation

- Empty keys rejected; path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
  in `services/api/app/service/files.py::validate_key`

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
