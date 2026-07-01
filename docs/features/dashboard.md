<!-- last_verified: 2026-06-30 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the interpolation pipeline's B2 story — the write-amplification ratio, render-output volume over time, and recent render jobs.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /jobs/stats`, `GET /jobs/stats/volume`, `GET /jobs`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (write amplification, source ingested, render output, jobs completed)
- `apps/web/src/components/dashboard/upload-chart.tsx` — render-output volume (MB/day) bar chart
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — recent render jobs
- `services/api/app/service/dashboard.py` — `get_dashboard_stats()`, `get_render_volume()`
- `services/api/app/repo/object_store.py` — `get_object_stats()` over `source/clips/` and `renders/`

## Canonical Files
- Stats service logic: `services/api/app/service/dashboard.py`
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically via TanStack Query)

## Outputs
- `GET /jobs/stats` → `DashboardStats` (total source/render bytes + human, **write_amplification_ratio**, jobs_completed, jobs_total, fps_minutes_processed)
- `GET /jobs/stats/volume?days=14` → `RenderVolumePoint[]` (render bytes per day)
- `GET /jobs` → `JobSummary[]` for the recent-jobs table

## Flow
- Page loads → parallel API calls (stats, volume, jobs)
- Stat cards show the hero **write-amplification ratio** (render ÷ source bytes) plus totals
- Volume chart shows render MB written to B2 per day over the last 14 days
- Recent-jobs table lists the latest jobs; a row click opens the job detail

## Edge Cases
- API unavailable → inline error states with retry
- No jobs yet → empty chart + empty table messages; amplification shows "—"/0x
- Large object count → stats paginate through all objects using `ContinuationToken`

## UX States
- Loading: skeleton cards / chart / table
- Empty: "No renders yet" / "No render jobs yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_engine.py` (run wiring produces the ratio), `test_structure.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest green, no ruff/eslint violations, `pnpm build` succeeds

## Related Docs
- [Write Amplification](write-amplification.md)
- [Interpolation Jobs](interpolation-jobs.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
