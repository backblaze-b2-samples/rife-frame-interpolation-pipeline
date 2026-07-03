<!-- last_verified: 2026-03-10 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `datetime.utcnow()` deprecated in Python 3.12+ | Naive datetimes, future breakage | Replace with `datetime.now(UTC)` in `repo/b2_client.py`, `service/metadata.py` | High | Resolved |
| S3 client recreated on every API call | Connection pool wasted, added latency | Cache client as module-level singleton via `lru_cache` | High | Resolved |
| `get_upload_stats()` pagination broken at 1000 objects | Stats silently wrong for large buckets | Check `IsTruncated` + use `ContinuationToken` | High | Resolved |
| `record_upload()` never called | `/metrics` always reports 0 uploads | Call from `runtime/upload.py` after successful upload | Medium | Resolved |
| Metrics counters not thread-safe | Race conditions under concurrent requests | Use `threading.Lock` (matches `service/files.py` pattern) | Medium | Resolved |
| `_humanize_bytes` duplicated in Python (repo + service) | DRY violation, drift risk | Extract to `app/types/formatting.py` shared util | Medium | Resolved |
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| `formatDate` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| No test harness for feature specs | No automated verification | Add pytest fixtures + test files per feature | Medium | Resolved (partial — tests added for upload, files, activity, errors) |

## 2026-07-03 — verify

Nitpicks surfaced by the 3-lens UX verify (blockers/frictions were fixed in the same pass; these are backlog-only):

- **/jobs/new (upload→create hand-off)** — the "Create render job" button on the upload-complete page lands on /jobs/new but the Source-clip combobox still reads "Select an uploaded clip…" → the just-uploaded clip is not pre-selected, so the user manually re-selects it (adversarial gate demoted this from friction to nitpick: correct page reached, selector works; a pre-fill would require query-param plumbing since the form's `source_key` is a B2 key while the upload item only carries `file.name`). (.local/lensA3_04_newjob_landed.png)
- **/jobs/new (cold start)** — the Source-clip helper text mentions that clips land under source/clips/ but there is no inline link/button to /upload → a first-time user with no clips must discover "Upload" in the left nav. (.local/lensA3_04_newjob_landed.png)
- **/jobs/[clip]/[multiplier] (active render)** — the status pill reads "pending" for the whole in-flight render (the B2 manifest only flips to completed/failed at the end; there is no intermediate "running" manifest) → the pill lags the true state, though the live progress card + advancing bar + stage text make the running state unmistakable. (.local/lensB3_06_running_midwaitA.png)
