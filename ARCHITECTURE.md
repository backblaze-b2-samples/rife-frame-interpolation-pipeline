<!-- last_verified: 2026-06-30 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with write-amplification metrics, render-volume chart, recent jobs
  - Render Jobs: create / read / run / delete interpolation jobs, live progress
  - Library: scoped explorer (source clips + renders) with inline `<video>` playback
  - Files: full-bucket explorer (kept from the starter kit)
  - Upload: drag-and-drop clip ingest into `source/clips/`
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for jobs (CRUD + run), library, files, upload
  - B2 S3 integration via boto3 (single + multipart)
  - **RIFE interpolation engine** (vendored Practical-RIFE HDv3) + ffmpeg encoder
  - Video clip metadata extraction (fps, duration, codec, resolution, bitrate)
  - Health check with B2 connectivity; structured JSON logging; `/metrics`
- **packages/shared/** — TypeScript types mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access + on-device model I/O — no business logic
  |        (b2_client, object_store, rife_engine, encoder, rife_vendor/)
service/   Business logic — calls repo, returns types
  |        (jobs, interpolation, dashboard, library, progress, files, upload, metadata)
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`.
2. No backward imports (e.g., service must not import from runtime).
3. `boto3` only in `repo/`. **CV/torch compute is also confined to `repo/`** (`rife_engine.py`, `encoder.py`, `rife_vendor/`), with all heavy imports **lazy** so the API boots and tests pass without the ML stack.
4. All boundary data uses Pydantic models (no raw dicts across layers).
5. Each Python file stays under 300 lines.

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  scripts/
    setup_rife.py          Fetch pinned RIFE weights from a HuggingFace mirror
    seed_demo.py           Generate + upload a synthetic demo clip (no committed binary)
  app/
    types/                 Pydantic models (jobs.py, files.py, stats.py, ...)
    config/                Settings loaded from environment
    repo/                  b2_client.py, object_store.py, rife_engine.py, encoder.py
      rife_vendor/         Vendored Practical-RIFE HDv3 arch (MIT) + LICENSE + NOTICE
    service/               jobs, interpolation, dashboard, library, progress, files, upload, metadata
    runtime/               FastAPI route handlers (jobs, library, files, upload, health, metrics)
  models/rife/             Fetched flownet.pkl (gitignored — never committed)
  tests/                   pytest (structural + wiring + engine + real RIFE smoke)
```

## The interpolation pipeline

A **job** is the primary entity — an immutable record of a (source clip, multiplier, codec)
transformation, persisted as a JSON manifest in B2. Running it executes:

```
source/clips/<clip>  --repo.download_to_file-->  local temp file
  --encoder.decode_frames (OpenCV)-->  RGB frames + source fps
  --rife_engine.interpolate_frames (vendored RIFE HDv3, device autodetect)-->
      (multiplier - 1) synthesized frames per adjacent pair
  --encoder.encode_frames (bundled imageio-ffmpeg, H.264/yuv420p/+faststart)-->  render.mp4
  --repo.multipart_upload_file-->  renders/<clip_id>/<multiplier>x/render.mp4
  --jobs.save_job-->  renders/<clip_id>/<multiplier>x/manifest.json  (status, sizes, ratio)
```

Runs execute in a FastAPI BackgroundTask thread. Live progress is tracked in an ephemeral,
process-local registry (`service/progress.py`); the **B2 manifest is authoritative**.

### Device selection (deployment: local)

`repo/rife_engine.select_device` auto-detects **CUDA → Apple MPS → CPU** and defaults to CPU.
No GPU is ever required. `MAX_SOURCE_FRAMES` caps a CPU demo. torch 2.6+ flips
`torch.load(weights_only=True)`; the trusted local checkpoint is loaded with `weights_only=False`.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). No application database.
  - `source/clips/` — ingested source clips.
  - `renders/<clip_id>/<multiplier>x/` — render output + per-job `manifest.json`.
  - Job registry = the set of `manifest.json` objects under `renders/`.
  - Listing/metadata via `list_objects_v2` / `head_object`; downloads via `get_object` /
    `download_file`; renders written via managed multipart `upload_file`; playback via
    `generate_presigned_url` (10-min expiry).

## External Services

- **Backblaze B2 S3 API** — the only external service. **No AI-provider API** — RIFE runs
  on-device, so the app runs on B2 credentials alone (no second key, no per-run cost).
- **HuggingFace Hub** — used once by `scripts/setup_rife.py` to fetch pinned model weights.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md).

- **Frontend -> API** — CORS-restricted. `CORSMiddleware` is registered LAST in `main.py`
  (outermost) so it wraps every response, including uncaught-exception 500s.
- **API -> B2** — authenticated via application keys, signature v4, region-derived endpoint.
- **Client -> B2** — presigned URLs for playback/download (short expiry).

## Data Flows

- **Ingest**: Browser -> `POST /upload` -> validate video -> repo writes `source/clips/<name>`.
- **Create job**: Browser -> `POST /jobs` -> write a `pending` manifest to B2.
- **Run**: Browser -> `POST /jobs/{clip}/{mult}/run` -> BackgroundTask runs the pipeline above.
- **Read / play**: `GET /jobs/{clip}/{mult}` (manifest) + `GET /jobs/{clip}/{mult}/render` (presigned).
- **Delete**: `DELETE /jobs/{clip}/{mult}` -> prefix-scoped delete of the job's render + manifest.
- **Library**: `GET /library` pairs each `source/clips/` object with its `renders/` outputs.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web :3000, api :8000).
- **Railway** — two services from the same repo. The interpolation service is CPU/GPU-heavy and
  runs long background jobs; see `infra/railway/README.md` for resource notes.

## Observability

- Structured JSON logging with `request_id`; request timing middleware (also the catch-all that
  converts uncaught exceptions to a typed JSON 500).
- `/metrics` (Prometheus format) and `/health` (B2 connectivity).

## Canonical Files

- Job orchestration: `services/api/app/service/interpolation.py`
- Job CRUD + manifests: `services/api/app/service/jobs.py`
- RIFE engine (device autodetect, weights_only): `services/api/app/repo/rife_engine.py`
- Encoder (OpenCV decode + bundled ffmpeg): `services/api/app/repo/encoder.py`
- Vendored model arch: `services/api/app/repo/rife_vendor/ifnet_hdv3.py`
- B2 object store (multipart, scoped delete): `services/api/app/repo/object_store.py`
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Interpolation Jobs](docs/features/interpolation-jobs.md)
- [Write Amplification](docs/features/write-amplification.md)
- [Media Library](docs/features/media-library.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) · [docs/RELIABILITY.md](docs/RELIABILITY.md) · [AGENTS.md](AGENTS.md)
