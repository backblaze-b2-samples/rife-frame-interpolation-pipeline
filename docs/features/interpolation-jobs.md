<!-- last_verified: 2026-06-30 -->
# Feature: Interpolation Jobs (primary entity)

## Purpose
Create, read, run, and delete a RIFE render job — an immutable record of turning a source clip into a high-frame-rate slow-motion render on B2.

## Used By
- UI: `/jobs` (list + create form dialog), `/jobs/new` (create), `/jobs/[clip]/[multiplier]` (detail/run/delete)
- API: `POST /jobs`, `GET /jobs`, `GET /jobs/{clip}/{mult}`, `POST /jobs/{clip}/{mult}/run`, `DELETE /jobs/{clip}/{mult}`, `GET /jobs/{clip}/{mult}/render`, `GET /jobs/progress`, `GET /jobs/sources`
- Job: FastAPI BackgroundTask thread runs the render; live progress in an ephemeral registry

## Core Functions
- `services/api/app/service/jobs.py` — `create_job`, `list_jobs`, `get_job`, `delete_job`, `list_source_clips`, key helpers
- `services/api/app/service/interpolation.py` — `run_interpolation` (download→decode→interpolate→encode→upload→manifest), `run_job` (background entry)
- `services/api/app/service/progress.py` — ephemeral run-progress registry
- `services/api/app/repo/rife_engine.py` — vendored RIFE model load + `interpolate_frames` (device autodetect)
- `services/api/app/repo/encoder.py` — OpenCV decode + bundled-ffmpeg encode
- `apps/web/src/components/jobs/create-job-form.tsx` — the create form (selectors + default hints)

## Canonical Files
- Orchestration exemplar: `services/api/app/service/interpolation.py`
- Create-form UX exemplar: `apps/web/src/components/jobs/create-job-form.tsx`

## Inputs
- `config.source_key`: string — a `source/clips/` object key (Select in the form)
- `config.multiplier`: 2 | 4 | 8 (RadioGroup)
- `config.codec`: "h264" | "h265" (Select; H.264 default)

## Outputs
- A `renders/<clip_id>/<multiplier>x/manifest.json` in B2 (`InterpolationJob`: status, source_fps, target_fps, source_bytes, render_bytes, amplification_ratio, render_key, timestamps)
- On run: `renders/<clip_id>/<multiplier>x/render.mp4` (browser-playable, multipart-uploaded)
- Side effects: B2 writes; a background thread; ephemeral progress updates

## Flow
- **create** → validate the source clip exists → write a `pending` manifest
- **run** → mark running → download clip → decode frames → RIFE interpolate → encode MP4 → multipart upload → write a `completed` manifest with sizes + amplification ratio
- **read** → fetch the manifest; if completed, resolve a presigned URL and play the render
- **delete** → prefix-scoped delete of the job's manifest + render
- **edit** → OMITTED by design (a job is immutable; create a new job to change parameters)

## Edge Cases
- Model/weights absent or torch missing → run fails with `status=failed`, `error="RIFE model not set up — run scripts/setup_rife.py"`; app still boots and every other flow works
- Source clip deleted before run → download raises; run recorded as failed with the error
- Re-run of a completed job → re-executes and overwrites the render + manifest
- Concurrent run of the same job → the in-flight run is returned (no double-run)

## UX States
- Empty: "No render jobs yet" with a create CTA
- Loading: skeleton rows; running: live progress bar (polled every 2s)
- Created (pending, never run): a "ready to run" hint, NOT the progress bar — the in-progress card is keyed on a live run-progress entry for the job, not on `status === "pending"`, so an idle job is visually distinct from an active render
- Error: failed badge + the actionable error message on the detail page
- Loaded: manifest table, write-amplification hero, `<video>` render player

## Verification
- Test files: `services/api/tests/test_engine.py` (device autodetect, key scoping, mocked run wiring), `services/api/tests/test_rife_smoke.py` (real un-mocked CPU interpolation, skipped without the ML stack)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: wiring test asserts the amplification ratio + completed manifest; the real smoke produces a genuine (non-average) interpolated frame

## Related Docs
- [Write Amplification](write-amplification.md)
- [Media Library](media-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
