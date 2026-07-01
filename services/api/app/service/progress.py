"""Process-local run-progress registry for interpolation jobs.

EPHEMERAL by design: this tracks *live* progress (pending -> running ->
completed/failed) for the UI's progress bar. It resets on restart and is not
shared across workers. The authoritative answer to "is this job done?" is the
manifest.json status in B2 (see service/jobs.py), never this registry.

Thread-safe so a FastAPI BackgroundTask thread can update progress while the
request thread reads it.
"""

from datetime import UTC, datetime
from threading import Lock

from app.types import JobStatus, RunProgress

_runs: dict[str, RunProgress] = {}
_lock = Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def start(job_id: str) -> RunProgress:
    """Register (or reset) a run's live progress and return it."""
    run = RunProgress(
        job_id=job_id, status="running", progress=0.0, updated_at=_now()
    )
    with _lock:
        _runs[job_id] = run
    return run


def update(
    job_id: str,
    *,
    status: JobStatus | None = None,
    progress: float | None = None,
    message: str | None = None,
    error: str | None = None,
) -> None:
    """Patch a run's live fields. No-op if the job id is unknown."""
    with _lock:
        run = _runs.get(job_id)
        if run is None:
            return
        data = run.model_dump()
        if status is not None:
            data["status"] = status
        if progress is not None:
            data["progress"] = progress
        if message is not None:
            data["message"] = message
        if error is not None:
            data["error"] = error
        data["updated_at"] = _now()
        _runs[job_id] = RunProgress(**data)


def get(job_id: str) -> RunProgress | None:
    with _lock:
        return _runs.get(job_id)


def list_runs() -> list[RunProgress]:
    with _lock:
        return sorted(_runs.values(), key=lambda r: r.updated_at, reverse=True)


def active(job_id: str) -> bool:
    """True if this job has a non-terminal in-flight run (avoid double-run)."""
    with _lock:
        run = _runs.get(job_id)
        return run is not None and run.status in ("pending", "running")
