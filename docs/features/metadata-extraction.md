<!-- last_verified: 2026-06-30 -->
# Feature: Video Clip Metadata Extraction

## Purpose
Extract video metadata from an uploaded clip and return it with the upload result. **fps is load-bearing** — the pipeline multiplies it to compute the target frame rate and the write-amplification ratio.

## Used By
- API: `POST /upload` (called after B2 upload)
- UI: upload results, file metadata panel

## Core Functions
- `services/api/app/service/metadata.py` — `extract_metadata()`, `_ffprobe_video()`
- `apps/web/src/components/files/file-metadata-panel.tsx` — displays metadata in a card

## Canonical Files
- Extraction pattern: `services/api/app/service/metadata.py`
- Display component: `apps/web/src/components/files/file-metadata-panel.tsx`

## Inputs
- file_data: bytes
- filename: string
- content_type: string (a `video/*` type)

## Outputs
- `FileMetadataDetail`: filename, size_bytes, size_human, mime_type, extension, md5, sha256, uploaded_at
- Video-specific (optional): **fps**, duration_seconds, codec, video_width, video_height, bitrate

## Flow
- Upload route stores the clip in B2
- `extract_metadata()` computes MD5 + SHA-256
- If the content type is `video/*`, `_ffprobe_video()` probes the clip with the ffprobe that ships alongside the **bundled imageio-ffmpeg binary** (no system ffmpeg) — parsing `avg_frame_rate` (a `num/den` rational) into fps, plus codec/resolution/duration/bitrate
- Returns a `FileMetadataDetail`

## Edge Cases
- Probe unavailable (ML stack not installed) → video fields stay null; hashes/size still returned; upload never blocked
- Corrupt / unreadable video → probe fails silently, video fields null
- `avg_frame_rate` of `0/0` → fps reported as null
- Image/PDF handling was intentionally **removed** — this app deals in video clips only

## UX States
- Not applicable (metadata is part of the upload response + file panel)

## Verification
- Test files: `services/api/tests/test_upload_conflict.py` (video-type acceptance / non-video rejection)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest green, no ruff violations

## Related Docs
- [File Upload](file-upload.md)
- [Interpolation Jobs](interpolation-jobs.md)
