<!-- last_verified: 2026-06-30 -->
# Feature: Write Amplification (the marquee B2 story)

## Purpose
Surface the pipeline's defining B2 characteristic: interpolation is write-heavy — a 4x render of a 1 TB source library produces 4+ TB of output. The dashboard reports the ratio of render bytes to source bytes.

## Used By
- UI: `/` dashboard (hero stat card) and `/jobs/[clip]/[multiplier]` (per-job amplification)
- API: `GET /jobs/stats` (`write_amplification_ratio`), `GET /jobs/{clip}/{mult}` (`amplification_ratio`)

## Core Functions
- `services/api/app/service/dashboard.py` — `get_dashboard_stats()` divides total render bytes by total source bytes across all objects
- `services/api/app/service/interpolation.py` — per-job `amplification_ratio = render_bytes / source_bytes`
- `services/api/app/repo/object_store.py` — `get_object_stats(prefix)` aggregates bytes under `source/clips/` and `renders/`

## Canonical Files
- Aggregation: `services/api/app/service/dashboard.py`

## Inputs
- None directly — derived from B2 object listings + job manifests

## Outputs
- Global ratio on the dashboard stat card
- Per-job ratio on the job detail (render size ÷ source size)

## Flow
- Each completed run records `source_bytes` (head_object on the clip) and `render_bytes` (uploaded render size) in its manifest
- The dashboard rolls up `get_object_stats("source/clips/")` and `get_object_stats("renders/")` and divides render ÷ source
- The result is the headline metric — higher multipliers and more jobs push it up, illustrating sustained write throughput to B2

## Edge Cases
- No source bytes yet → ratio reported as 0.0 (avoids divide-by-zero)
- Renders present but sources deleted → ratio can exceed the multiplier; that's expected (the payload persists on B2 independent of the source)

## Verification
- Test files: `services/api/tests/test_engine.py::test_run_interpolation_wiring_with_mocked_engine` asserts `amplification_ratio == render_bytes / source_bytes`
- Quick verify command: `pnpm test:api`
- Pass criteria: the wiring test computes 4.0 for a 1000B source / 4000B render

## Related Docs
- [Dashboard](dashboard.md)
- [Interpolation Jobs](interpolation-jobs.md)
