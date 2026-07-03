<!-- last_verified: 2026-06-30 -->
# App Workflows

User journeys inside the application.

## Ingest a clip → render slow motion (the primary journey)

1. **Upload** — user navigates to `/upload`, drops a source video clip (MP4/MOV/WebM/MKV/AVI, up to 500MB). It lands under `source/clips/` on B2. (Or run `pnpm seed:demo` to add a synthetic clip.) Once a clip finishes uploading, a **Create render job** button links straight to `/jobs/new` so the next step is one click away.
2. **Create a job** — user goes to `/jobs` → **New render job**, picks the source clip (Select), a multiplier (2x / 4x / 8x, RadioGroup), and a codec (H.264 / H.265, Select). A `pending` job manifest is written to B2. Target fps = source fps × multiplier (derived on run).
3. **Run** — user opens the job detail (`/jobs/[clip]/[multiplier]`) and clicks **Run**. A background render executes: download → decode → RIFE interpolate → encode MP4 → multipart upload → manifest update. A live progress bar polls every 2s.
4. **Play** — on completion, the write-amplification ratio and manifest appear, and the rendered slow-mo plays inline in an HTML5 `<video>` via a presigned URL.
5. See: [Interpolation Jobs](features/interpolation-jobs.md)

## Browse the media library

- User navigates to `/library` (scoped to this app's `source/clips/` + `renders/`)
- Each source clip is listed with the renders derived from it and their status
- Play a source clip or any render inline; empty clips prompt to create a job
- See: [Media Library](features/media-library.md)

## Browse and manage the full bucket

- User navigates to `/files` (the full-bucket explorer, kept from the starter kit)
- Files shown in a tree; hover a row for preview / download / delete
- See: [File Browser](features/file-browser.md)

## View the dashboard

- User navigates to `/` (home)
- Parallel API calls load: interpolation stats, render volume, recent jobs
- Stat cards show the **write-amplification ratio**, source ingested, render output, jobs completed
- The chart shows render MB written to B2 per day; the table lists recent jobs
- See: [Dashboard](features/dashboard.md) · [Write Amplification](features/write-amplification.md)
