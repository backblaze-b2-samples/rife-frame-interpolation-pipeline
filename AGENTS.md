<!-- last_verified: 2026-06-25 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/         Dashboard (/), jobs, jobs/new, jobs/[clip]/[multiplier], library,
                   upload, files, settings, design
  src/components/  dashboard/, jobs/, library/, files/, upload/, settings/, layout/, ui/ (generated)
  src/lib/         api-client.ts, queries.ts (TanStack), job-format.ts, app-config.ts
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/        b2_client, object_store (boto3); rife_engine, encoder (torch/cv2, LAZY);
                   rife_vendor/ (vendored Practical-RIFE HDv3 arch, MIT)
  app/service/     jobs, interpolation, dashboard, library, progress, files, upload, metadata
  scripts/         setup_rife.py (fetch pinned weights), seed_demo.py (synthetic clip)
  requirements.txt + requirements-ml.txt   base vs heavy torch/CV stack
packages/shared/   Shared TypeScript types (mirrors Pydantic models)
docs/              System of record (features, workflows, security, reliability)
infra/railway/     Deployment config
```

## 2. The Realized Contract (built on the starter kit)

This app was built on the vibe-coding-starter-kit. The starter contract was honored as follows — keep these distinctions when extending.

**Kept verbatim (do not strip, rename, or edit)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit generated `components/ui/` files. Restyle via tokens.
- **Bucket Explorer (Files).** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/` — the full-bucket browse. Its sidebar entry stays. This app *also* adds a scoped **Library** explorer; the two coexist: Files = whole bucket, Library = this app's own `source/clips/` + `renders/` prefixes.
- **Upload.** `/upload` route and `apps/web/src/components/upload/` — narrowed to video-clip ingest, writing to `source/clips/`.

**Added for this app**
- **Render Jobs** (`/jobs`, `/jobs/new`, `/jobs/[clip]/[multiplier]`) — the primary entity (InterpolationJob): create / read / run-with-live-progress / delete. Edit is intentionally omitted (see §2b).
- New backend: `runtime/{jobs,library}.py`, `service/{jobs,interpolation,dashboard,library,progress}.py`, `repo/{object_store,rife_engine,encoder}.py`, `repo/rife_vendor/`, `types/jobs.py`.
- **Scripts:** `scripts/setup_rife.py` (`pnpm setup:rife`), `scripts/seed_demo.py` (`pnpm seed:demo`).

**Adapted**
- **Dashboard.** `/` and `apps/web/src/components/dashboard/` show interpolation metrics (write amplification, source/render bytes, jobs completed) + a render-volume chart + recent jobs. Aggregations flow through `runtime -> service -> repo` and TanStack Query hooks in `lib/queries.ts` — no bare `useEffect + fetch`.
- **Settings.** `settings-form.tsx` is the form-UX exemplar (selectors + default hints) and now exposes interpolation defaults (default multiplier + codec, demo-only).

**Trimmed**
- Image/PDF metadata extraction (old `service/metadata.py` branches, Pillow/PyPDF2 deps, `FileMetadataDetail.image_*/exif/pdf_*` fields) — this app deals in **video clips only**. Video metadata (fps/duration/codec/resolution/bitrate) is kept; **fps is load-bearing** for target-fps + amplification.

### 2b. Primary-entity lifecycle (InterpolationJob)

create / read / run / delete are all built in the UI. **Edit is omitted by design:** a job is an *immutable record* of a (source clip, multiplier, codec) transformation — its render is deterministic from those inputs. Changing parameters defines a *different* render, so the UX is "create a new job," not "edit one." The create form (`components/jobs/create-job-form.tsx`) already exposes every parameter.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/` (both `b2_client.py` and `object_store.py` live there)
- **On-device compute is confined to `repo/`**: `rife_engine.py` (RIFE model), `encoder.py` (OpenCV decode + bundled ffmpeg), `rife_vendor/` (the model architecture). All torch / cv2 / imageio_ffmpeg imports are **lazy** so the API boots and `pnpm test:api` / `pnpm check:structure` pass without `requirements-ml.txt`.
- **Device selection auto-detects CUDA → MPS → CPU and defaults to CPU** (`repo/rife_engine.select_device`); never hard-require a GPU. `MAX_SOURCE_FRAMES` caps a CPU demo. torch 2.6+'s `weights_only` flip is handled by loading the trusted local checkpoint with `weights_only=False`.
- **Keyless by default**: RIFE runs on-device — no AI-provider key. The app runs end-to-end on B2 credentials alone. `setup_rife.py` fetches pinned weights from a HuggingFace mirror.
- **Job deletes are prefix-scoped** to `renders/<clip_id>/<multiplier>x/` (`object_store.delete_prefix` refuses an empty / root / bare `renders/` prefix).
- No business logic in route handlers (`runtime/`); all boundary data is a Pydantic model.
- The only module-level mutable state is the explicitly-ephemeral run-progress registry (`service/progress.py`); B2 manifests are authoritative.

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| Engine imports without ML stack | `tests/test_engine.py::test_engine_imports_without_ml_stack` |
| Device never requires a GPU | `tests/test_engine.py::test_device_defaults_to_cpu_without_torch` |
| Run wiring (no torch/ffmpeg needed) | `tests/test_engine.py::test_run_interpolation_wiring_with_mocked_engine` |
| No bare print() | `ruff` rule T20 (scripts/ excepted) |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint (none of these need the ML stack)
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests

# Interpolation pipeline (one-time enablement)
pnpm setup:rife        # fetch the pinned RIFE weights into services/api/models/rife/
pnpm seed:demo         # generate + upload a synthetic demo clip to source/clips/
#   Enable the engine first:
#     cd services/api && source .venv/bin/activate && pip install -r requirements-ml.txt
#   ffmpeg is bundled via imageio-ffmpeg (no system install). Use Python <= 3.11.
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
