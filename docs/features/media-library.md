<!-- last_verified: 2026-06-30 -->
# Feature: Media Library (scoped explorer)

## Purpose
Browse this app's own media — source clips under `source/clips/` and the renders derived from each — with inline playback. Distinct from the full-bucket Files explorer (which stays); the Library is scoped to the app's two prefixes.

## Used By
- UI: `/library` page + **Library** sidebar entry
- API: `GET /library`, `GET /library/play?key=<key>`

## Core Functions
- `services/api/app/service/library.py` — `list_library()` pairs each source clip with its renders (by derived clip_id)
- `services/api/app/runtime/library.py` — list + presigned playback URL
- `apps/web/src/components/library/media-library.tsx` — the scoped explorer UI

## Canonical Files
- Service: `services/api/app/service/library.py`

## Inputs
- None to list; `key` (a `source/clips/` or `renders/` object) for playback

## Outputs
- `GET /library` → `LibraryClip[]` (each with `renders: LibraryRender[]`)
- `GET /library/play` → `{ url }` presigned playback URL

## Flow
- List all `source/clips/` objects → for each, derive its `clip_id` and attach the `.mp4` renders under `renders/<clip_id>/` (with each render's status pulled from its manifest)
- The UI plays a clip or a render inline in a shared `<video>` element via a presigned URL

## Edge Cases
- Clip with no renders → shown with a "create a job for this clip" hint
- API/presign failure → the player simply doesn't open; the list still renders
- Only this app's prefixes are listed — never the whole bucket (that's Files)

## UX States
- Empty: "Library is empty" with an upload CTA
- Loading: skeletons
- Loaded: one card per clip, each listing its renders with play buttons

## Verification
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: `/library` renders clips + renders; playback opens a presigned `<video>`

## Related Docs
- [File Browser](file-browser.md) (the full-bucket explorer)
- [Interpolation Jobs](interpolation-jobs.md)
