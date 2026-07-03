# Build Plan — `rife-frame-interpolation-pipeline`

> Source of truth for the starter-kit tree: `.claude/scratch/vcsk-492673d8-7eca-4d3b-b0b5-6a0560e00486/`
> (cloned fresh in Phase 0). All keep/trim/add deltas are computed against that tree.

---

## 1. Purpose

`rife-frame-interpolation-pipeline` is a B2-backed video post-production pipeline that turns
standard-frame-rate footage into high-frame-rate slow-motion renders. A user ingests source clips
(24/30/60 fps) into Backblaze B2 under `source/clips/`, then creates an **interpolation job** that
runs **Practical-RIFE** (optical-flow neural frame interpolation) locally to synthesize intermediate
frames, re-encodes the result to MP4 at 2× / 4× / 8× the original frame rate, and writes the render
back to B2 under `renders/<clip_id>/<multiplier>/`. It's for sports-analytics teams,
cinematographers, and game studios who need self-hosted slow-mo without a second API key — **B2
credentials only**. The marquee B2 story is **write amplification**: a 4× interpolation of a 1 TB
source library produces 4+ TB of render output, and continuous batch jobs sustain high write
throughput — a classic write-heavy workload that B2 is ideal for. The app surfaces that ratio
(render bytes ÷ source bytes) front and center on the dashboard.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the **ceiling**: keep the shared B2 scaffolding, strip what a frame-interpolation
app doesn't need, add the interpolation engine + job lifecycle + scoped media library.

### KEEP (as-is, do not strip/rename the contract pieces)
- **UI kit / design system** — `apps/web/src/components/ui/` (shadcn primitives), tokens in
  `apps/web/src/app/globals.css`, and the `/design` reference page. Restyle via tokens only.
- **Bucket explorer (NON-NEGOTIABLE keep)** — `/files` route, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`, and the **Files** sidebar entry. Full-bucket browse stays.
- **Upload** — `/upload` route + `apps/web/src/components/upload/` + the **Upload** sidebar entry.
  This is the clip-ingest surface (uploads land in `source/clips/`).
- **Settings** (`/settings`) + **Design System** sidebar entries.
- **Layered FastAPI backbone** — `types → config → repo → service → runtime`, the structural tests,
  ruff/eslint config, `/health`, `/metrics`, structured JSON logging, the `timing_middleware`
  exception→500 path, CORS-last ordering, the doctor preflight, TanStack Query data layer
  (`lib/queries.ts` + `lib/api-client.ts`), `lib/app-config.ts` single-rebrand point.
- **Metadata extraction plumbing** — `service/metadata.py`, but narrowed to **video** (see TRIM).

### TRIM (remove / narrow)
- **Image & PDF metadata extraction** in `service/metadata.py` (EXIF, dimensions, PDF pages/author)
  and the Pillow / PyPDF2 deps in `requirements.txt`. This app deals in **video clips only** — keep
  video metadata (duration, **fps**, codec, resolution, bitrate), which the pipeline genuinely needs
  to compute target fps and the amplification ratio. Drop the image/PDF branches + their `FileMetadataDetail`
  fields (`image_*`, `exif`, `pdf_*`).
- **Dashboard default tiles** — the starter's "total files / uploads today / 7-day upload chart" are
  illustrative defaults; replace with interpolation-relevant metrics (see ADD → Dashboard).
- **Settings preferences fields** — the starter's `defaultView / emailOnUpload / warnNearQuota /
  quotaThreshold` are illustrative; replace with interpolation defaults (default multiplier, default
  codec) — still demo-only (no API), still using the Select/RadioGroup/FormDescription exemplar.

### ADD (new for this sample)
- **Primary entity: Interpolation Job** — see §4 for the full lifecycle. New routes:
  - `/jobs` — job list + "New render job" create form (dialog) + per-row run/delete/open.
  - `/jobs/[id]` — job detail (read): manifest, source vs render size, amplification ratio, status,
    and an HTML5 `<video>` that plays the rendered slow-mo via a presigned URL; run/delete actions.
- **Scoped media library (MANDATORY scoped-explorer add)** — `/library` route: a sample-specific
  asset explorer scoped to **`source/clips/`** and **`renders/`** only (the app's own folders),
  distinct from the full-bucket `/files` explorer which stays. Shows clips and their renders with
  inline playback. Sidebar entry: **Library**.
- **RIFE interpolation engine** — vendored Practical-RIFE model + weights (see §7 RISKS for the
  reproducibility-critical details). New repo-layer adapters:
  - `repo/rife_engine.py` — loads the RIFE model (device autodetect CUDA → MPS → CPU, **CPU default**),
    exposes `interpolate_clip(...)`. Heavy imports (`torch`, vendored model) contained here.
  - `repo/encoder.py` — ffmpeg adapter using the **bundled imageio-ffmpeg binary**; decode via
    OpenCV, encode via ffmpeg (libx264/MP4 default — see §7). Heavy imports contained here.
  - `repo/rife_vendor/` — vendored Practical-RIFE model architecture (pinned commit) + upstream MIT
    LICENSE + attribution NOTICE.
- **Job orchestration** — `service/interpolation.py` (download→decode→interpolate→encode→upload→
  manifest, run in a background thread, status persisted) and `service/jobs.py` (create/list/get/
  run/delete over B2-stored manifests).
- **Job manifest storage in B2** — no database (B2 is the sole store, per starter). Each job is a
  JSON object at `renders/<clip_id>/<multiplier>/manifest.json`: `{job_id, source_key, source_fps,
  target_fps, multiplier, codec, status, source_bytes, render_bytes, amplification_ratio,
  render_key, created_at, completed_at, error}`.
- **Dashboard (adapted)** — tiles: total source bytes, total render bytes, **write-amplification
  ratio** (render ÷ source, the hero metric), jobs completed, fps-minutes processed; a chart of
  render-output volume over time; a recent-jobs table. New aggregation flows through
  `runtime → service → repo` and a TanStack Query hook.
- **Seed script** — `scripts/seed_demo.py`: generates a short synthetic clip with the bundled ffmpeg
  (`testsrc`/`mandelbrot`, ~2 s @ 24 fps, small resolution) and uploads it to `source/clips/`, so a
  fresh clone has a clip to interpolate **without committing any binary asset**.

### Bucket-explorer tension note
None — `/files` (full bucket) stays as a first-class surface, and `/library` is the additional
scoped explorer. Both are present; the contract is satisfied cleanly.

## 3. B2 surface (S3-compatible only — no b2-native)

All access via the boto3 S3 client in `repo/` (custom `user_agent_extra` preserved). Operations:
- `put_object` / `upload_fileobj` (clip ingest, manifest JSON write).
- **Multipart upload** (`upload_file` / `TransferConfig`) for **render output** — renders are large
  (the write-amplification payload); boto3's managed transfer handles multipart automatically.
- `list_objects_v2` (job list = list manifests; `/library` scoped list; `/files` full list;
  clip-selector list for the create form; dashboard aggregation).
- `head_object` (source/render byte sizes for the amplification ratio).
- `get_object` (download source clip to a temp file for processing).
- `generate_presigned_url` (serve renders to the `<video>` player; downloads — 10-min expiry).
- `delete_object` / `delete_objects` (**delete a job's renders, scoped strictly to that job's
  `renders/<clip_id>/<multiplier>/` prefix** — never a broad delete; see CLAUDE.local.md safety rule).

**No b2-native API anywhere.** No justified deviations required.

## 4. Key features (seed README + `docs/features/<feature>.md`)

1. **Interpolation jobs (primary entity)** — create/read/run/delete a RIFE render job.
   `deployment: local` · provider: **none** (Practical-RIFE runs on-device) · cost/run: **$0**
   (B2 storage only, no second API key) · key env var: none (CPU-default, CUDA/MPS auto-detected).
2. **RIFE neural interpolation engine** — Practical-RIFE optical-flow model, local.
   `deployment: local` · provider: **none** · cost/run: **$0** · CPU default / GPU autodetect
   (CUDA → MPS → CPU) per `api-provider-selection.md` hard rule for on-device workloads.
3. **H.264/MP4 re-encode** — interpolated frames → browser-playable MP4 (codec env-configurable).
4. **Write-amplification dashboard** — render-bytes ÷ source-bytes, the marquee B2 story.
5. **Scoped media library** — browse this app's `source/clips/` + `renders/` with inline playback.
6. **Clip ingest + full bucket explorer** — drag-drop upload to `source/clips/`; full-bucket browse.

**No external API provider** for any feature → no provider-key env vars, no remote cost.
**No Genblaze** — the use case explicitly says "no second API key, B2 credentials only" and does not
mention Genblaze/`genblaze-*`, so provider calls are NOT routed through the Genblaze SDK.

### Primary-entity lifecycle (Interpolation Job)
| Verb | Built? | Notes |
|------|--------|-------|
| **create** | ✅ UI | "New render job" form: pick source clip + multiplier + codec → writes a `pending` manifest. |
| **read** | ✅ UI | `/jobs/[id]` detail: manifest, sizes, amplification ratio, status, render playback. |
| **run** | ✅ UI | "Run"/"Re-run" button: executes RIFE→encode→upload, updates status pending→running→completed/failed. |
| **delete** | ✅ UI | Removes the job manifest + its renders (scoped to the job prefix). |
| **edit** | ❌ OMITTED | **UX justification:** an interpolation job is an *immutable record* of a (source clip, target fps, codec) transformation — its output is deterministic from those inputs. Changing parameters doesn't mutate a render; it defines a *different* render. So the UX is "create a new job," not "edit an existing one." The create form already exposes every parameter. → recorded in `omitted_ui_verbs`. |

### Form UX conventions — the **create-job** form (primary)
- **Finite-value fields use selectors, never free text:**
  - *Source clip* → `Select` populated from `source/clips/` (list_objects_v2).
  - *Multiplier* → `RadioGroup` / segmented control: **2× / 4× / 8×**.
  - *Output codec* → `Select`: **H.264 (MP4)** / H.265 (HEVC).
  - *Target fps* → derived (`source_fps × multiplier`), shown read-only via `FormDescription` — not a text input.
- **Create-form safe defaults as guidance (placeholder / `FormDescription`, never an autofill button):**
  default multiplier **2×**, default codec **H.264 (MP4)**; `FormDescription` on each field; a hint
  like "Start with a short clip at 2× for a fast first render." No button that fills the form.
- Exemplar to mirror: `apps/web/src/components/settings/settings-form.tsx` (RadioGroup for the
  theme enum, Select for default-view, `FormDescription` helper text throughout).
- (No edit form — edit verb omitted with justification above.)

## 5. Doc transforms
- **README.md** — full rewrite: purpose, 5-step pipeline (ingest→interpolate→encode→store→serve),
  the write-amplification narrative, quickstart **including** `scripts/setup_rife.py` (model fetch),
  the **Python ≤ 3.11** constraint (RIFE), the ffmpeg note (bundled binary, no system dep), and the
  CPU-default / GPU-autodetect behavior. Keep the B2 sign-up UTM links (content tag `b2ai-oss-start`).
- **ARCHITECTURE.md** — components (+ RIFE engine, encoder, job manifests, library), data flows
  (ingest/interpolate/encode/store/serve), data stores (B2 holds clips + renders + manifests; still
  no DB), deployment note (interpolation is CPU/GPU-heavy and long-running).
- **AGENTS.md** — repo map, the "Building on This Starter Kit" section reframed as this app's actual
  contract, commands (+ `setup_rife`, `seed_demo`, ML install), the new env var names.
- **docs/features/** — rewrite `dashboard.md` (write-amp metrics); keep+rename `file-browser.md`
  (bucket explorer) and `file-upload.md` (clip ingest); adapt `metadata-extraction.md` → video clip
  metadata (fps detection). **ADD:** `interpolation-jobs.md`, `media-library.md`,
  `write-amplification.md`. Keep `_template.md`.
- **docs/SECURITY.md / RELIABILITY.md** — rename + note: large-file (multipart) handling, presigned
  playback URLs, long-running background jobs and their failure/status semantics.
- **docs/app-workflows.md / dev-workflows.md** — new journey (ingest clip → create job → run → play
  render) and the ML/model-setup dev workflow.
- **infra/railway/README.md** — note the torch/ffmpeg/CPU resource needs for the interpolation service.

## 6. Rename table (`vibe-coding-starter-kit` → `rife-frame-interpolation-pipeline`)
| Form | From | To |
|------|------|----|
| kebab / repo slug | `vibe-coding-starter-kit` | `rife-frame-interpolation-pipeline` |
| Title Case | `Vibe Coding Starter Kit` | `RIFE Frame Interpolation Pipeline` |
| snake (if any) | `vibe_coding_starter_kit` | `rife_frame_interpolation_pipeline` |
| pkg scope | `@vibe-coding-starter-kit/web`, `@vibe-coding-starter-kit/shared` | `@rife-frame-interpolation-pipeline/web`, `@rife-frame-interpolation-pipeline/shared` |
| root pkg name | `vibe-coding-starter-kit` | `rife-frame-interpolation-pipeline` |
| `APP_NAME` (lib/app-config.ts) | `"OSS Starter Kit"` | `"RIFE Frame Interpolation Pipeline"` |
| `APP_DESCRIPTION` | `"File management dashboard powered by Backblaze B2"` | `"High-frame-rate slow-motion render pipeline powered by Backblaze B2"` |
| image tags / workflow slugs (infra/railway) | `vibe-coding-starter-kit*` | `rife-frame-interpolation-pipeline*` |
| UTM content tag | `b2ai-oss-start` | **unchanged** (program-wide tag, not the app name) |

**Synchronize all ~35 occurrences** found by the architecture map (root + `apps/web` + `packages/shared`
`package.json`, `next.config.ts` `transpilePackages`, every `@vibe-coding-starter-kit/shared` import in
`apps/web/src/**`, README/docs clone+filter commands). After rename, `pnpm install` must re-resolve
the workspace and `pnpm build` / `pnpm lint` must pass.

**Branding-leak check (known issue):** verify `apps/web/src/components/layout/header.tsx` derives the
title from `APP_NAME` + pathname and does NOT hardcode "oss-starter-kit" or a "Page" fallback; fix to a
single `APP_NAME` const + pathname-derived title if it does. Check the sidebar footer too.

---

## 7. RISKS & hard requirements (the reproducibility-critical part — reviewer must gate on these)

**R1 — RIFE is the real engine (vendor fidelity, non-negotiable).** Use actual Practical-RIFE neural
interpolation, NOT an ffmpeg `minterpolate`/`tblend` substitute. A sample themed on Practical-RIFE
must run Practical-RIFE.

**R2 — Reproducible model weights (this is the #1 hazard).** Upstream distributes `flownet.pkl` only
via **Google Drive / Baidu** — unusable for automated/clean-install. Instead:
- Vendor the RIFE **model architecture** (`.py`) at a **pinned commit** of hzwer/Practical-RIFE into
  `repo/rife_vendor/` (MIT — include upstream LICENSE + attribution).
- Fetch **`flownet.pkl` from a pinned HuggingFace mirror** via `huggingface_hub.hf_hub_download`
  (repo + **revision** pinned) in `scripts/setup_rife.py`, into `services/api/models/rife/`
  (gitignored). Make repo/file/revision env-configurable (`RIFE_WEIGHTS_HF_REPO`,
  `RIFE_WEIGHTS_HF_FILE`, `RIFE_WEIGHTS_HF_REVISION`, `RIFE_MODEL_DIR`).
- **The architecture `.py` must match the weights version.** The builder MUST verify a matching
  arch+weights pair actually loads and produces a valid interpolated frame on CPU. If it cannot
  confirm a working pair, raise it as an open question — do **not** ship a stub that imports but
  never interpolates.

**R3 — Pinned ML deps in a separate `requirements-ml.txt`** (boots+tests passing while the ML
feature is broken on a fresh clone is a known false-green). Pin a working window: `torch`/`torchvision`
(a 2.x window with a CPU wheel), **`numpy<2`**, `opencv-python-headless`, `huggingface_hub`,
`imageio-ffmpeg`, `tqdm`. **Avoid `sk-video` and `moviepy`** (upstream RIFE deps that are fragile on
py3.11/arm64 — we replace them with OpenCV decode + imageio-ffmpeg encode).

**R4 — torch ≥ 2.6 `weights_only` trap.** `torch.load` defaults to `weights_only=True` and will fail
on `flownet.pkl`. Load the trusted local checkpoint with `weights_only=False` (or
`torch.serialization.add_safe_globals`). Apply at the model-load site in `repo/rife_engine.py`.

**R5 — Browser-playable render codec.** Default encode is **H.264 (libx264) in MP4** with `yuv420p`
and `+faststart` so renders actually paint in the `<video>` element (the downstream verify/screenshot
steps require media to render). H.265/HEVC won't play in Chrome reliably — keep it as an opt-in codec
choice, but default to H.264. Note this as a deliberate deviation from the use case's "MP4/H.265"
wording, justified by browser playability.

**R6 — ffmpeg via bundled binary.** Resolve the encoder through `imageio_ffmpeg.get_ffmpeg_exe()`,
not bare system `ffmpeg` (Homebrew ffmpeg ships slim). We only need libx264/libx265 (no
subtitles/drawtext), but the bundled binary guarantees codec availability regardless of host.

**R7 — Graceful degradation.** If weights/model are missing or torch is unavailable, a job run must
fail with an **actionable error** (status=`failed`, `error="RIFE model not set up — run
scripts/setup_rife.py"`) — the app must still **boot** and every B2/UI flow (upload, library, bucket
explorer, dashboard, job CRUD) must work without the model present.

**R8 — Python ≤ 3.11** (RIFE constraint). `doctor.mjs` should warn if Python > 3.11.

**R9 — No-network signature-guard test.** Add a backend test that imports the engine module and
exercises the interpolation orchestration with a **mocked** engine (no weight download, no torch run)
so CI catches wiring drift without needing the model — plus a real (un-mocked) smoke the builder runs
locally if feasible.

**R10 — B2 standards (#3 env vars — required transform from the starter's deviation).** The starter
uses `B2_KEY_ID` / `B2_ENDPOINT` / `B2_PUBLIC_URL` and **no** `B2_REGION`. Rename to the standardized
names everywhere (`settings.py`, `.env.example`, `doctor.mjs`, README, infra):
- `B2_KEY_ID` → **`B2_APPLICATION_KEY_ID`**
- add **`B2_REGION`** (build `endpoint_url = https://s3.{B2_REGION}.backblazeb2.com` and pass
  `region_name=B2_REGION` to boto3)
- `B2_PUBLIC_URL` → **`B2_PUBLIC_URL_BASE`**
- keep `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`.
Update `doctor.mjs` to check the new names. Preserve the custom `user_agent_extra` on the S3 client
(keep `b2ai-oss-start`). These are the three `/b2-doctor` standards — treat deviations as defects.

**R11 — Size discipline.** 300-line file limit is structurally enforced — split the interpolation
service / engine / encoder / jobs router accordingly. Keep `boto3` only in `repo/`.

**R12 — No binary assets committed.** The demo clip is generated at runtime by `scripts/seed_demo.py`
(ffmpeg `testsrc`), not committed. (Screenshots/logos are later pipeline steps, not this one.)

---

## 8. Acceptance criteria (for the reviewer)
- ✅ All three B2 standards: S3-only, custom UA on every client, standardized `B2_*` names (R10).
- ✅ Real Practical-RIFE engine wired (not a stub / not ffmpeg-minterpolate) (R1).
- ✅ Weights fetched from a pinned reproducible source via a documented setup script (R2);
  ML deps pinned in `requirements-ml.txt` with numpy<2 and no sk-video/moviepy (R3).
- ✅ CPU default + CUDA/MPS autodetect (R2); torch weights_only handled (R4).
- ✅ Default render codec H.264/MP4, browser-playable, via bundled ffmpeg (R5/R6).
- ✅ App boots and all B2/UI flows work even with the model absent (R7).
- ✅ Primary-entity lifecycle: create/read/run/delete built in the UI; edit omitted **with** the
  recorded UX justification; create form uses selectors + default hints (§4).
- ✅ Bucket explorer (`/files`) kept; scoped `/library` explorer added.
- ✅ Rename complete & consistent; `pnpm install/lint/build`, `pnpm lint:api`, `pnpm test:api`,
  `pnpm check:structure` pass; no `@vibe-coding-starter-kit` references remain; header branding fixed.
- ✅ Docs transformed per §5; plan moved to `docs/exec-plans/completed/` on PASS.
