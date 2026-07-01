<!-- last_verified: 2026-06-25 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients
- Uncaught exceptions are converted to a typed JSON 500 (`{"detail": "Internal server error"}`, modeled by `app.types.ErrorResponse`) by the catch-all in `timing_middleware`
- **Error responses carry CORS headers.** `CORSMiddleware` is registered LAST in `main.py` so it is the outermost middleware and wraps every response — including uncaught-exception 500s produced by the inner catch-all. This is intentional and load-bearing: if a 500 shipped without `Access-Control-Allow-Origin`, the browser would block it and the frontend would surface only an opaque "network error", hiding the real server bug. Regression-guarded by `tests/test_error_handling.py::test_unhandled_exception_500_carries_cors_headers`.

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Video metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure
- **The app boots and every B2/UI flow works without the RIFE model present.** If the weights
  are missing or torch isn't installed, a job run fails with an actionable manifest error
  (`status=failed`, `error="RIFE model not set up — run scripts/setup_rife.py"`) instead of
  crashing. Upload, library, files, dashboard, and job CRUD all work model-free.

## Long-running render jobs

- Renders run in a FastAPI **BackgroundTask thread**; the HTTP request returns immediately with
  a `RunProgress` and the UI polls `GET /jobs/progress` every 2s while a render is in flight.
- The **authoritative** job status is the `manifest.json` in B2 (`pending` → `running` →
  `completed` / `failed`), not the ephemeral in-process progress registry (which resets on
  restart and is per-worker).
- Any failure in the pipeline is caught in `service/interpolation.run_job` and recorded on both
  the run and the manifest, so a crashed render never leaves the UI stuck "running" after a reload.
- A second run request for a job already in flight returns the existing run (no double-run).

## Large-file handling

- Render output uploads via boto3's managed multipart transfer, so a multi-GB render never
  buffers entirely in memory.

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
