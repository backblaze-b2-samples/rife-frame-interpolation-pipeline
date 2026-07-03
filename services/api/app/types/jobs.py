"""Pydantic models for the RIFE interpolation pipeline.

Pure data — no logic, no imports from other app layers (types is the bottom
layer). These are the contract shared with the frontend via
packages/shared/src/types.ts.
"""

from typing import Literal

from pydantic import BaseModel

# A job's persisted lifecycle status (authoritative, stored in the B2 manifest).
JobStatus = Literal["pending", "running", "completed", "failed"]

# Interpolation multipliers offered in the create form (RadioGroup).
Multiplier = Literal[2, 4, 8]

# Output codecs offered in the create form (Select). H.264/MP4 is the
# browser-playable default; H.265/HEVC is opt-in (may not play in Chrome).
Codec = Literal["h264", "h265"]


class JobConfig(BaseModel):
    """The (immutable) transformation an interpolation job describes."""

    # The source clip this render is built from (a source/clips/ object key).
    source_key: str
    # Slow-motion factor: the render keeps the source fps but holds multiplier x
    # the frames, so it lasts multiplier x longer and plays at 1/multiplier speed.
    multiplier: Multiplier = 2
    # Output codec — h264 (MP4, default, browser-playable) or h265 (HEVC).
    codec: Codec = "h264"


class InterpolationJob(BaseModel):
    """Primary entity. Persisted at renders/<clip_id>/<multiplier>/manifest.json.

    A job is an immutable record of a (source clip, multiplier, codec)
    transformation — its render output is deterministic from those inputs.
    """

    job_id: str
    config: JobConfig
    status: JobStatus = "pending"
    # Source clip frame rate (populated once a run reads the source). The render
    # plays back at this same fps -- that is what makes it slow motion. Playback
    # speed and duration are derived from source_fps + config.multiplier.
    source_fps: float | None = None
    # Byte sizes + the marquee B2 metric: render_bytes / source_bytes.
    source_bytes: int = 0
    render_bytes: int = 0
    amplification_ratio: float | None = None
    # B2 key of the rendered slow-motion output (once completed).
    render_key: str | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


class JobSummary(BaseModel):
    """Lightweight job row for the list view (no per-run detail beyond stats)."""

    job_id: str
    source_key: str
    source_filename: str
    multiplier: int
    codec: str
    status: JobStatus
    source_bytes: int = 0
    render_bytes: int = 0
    amplification_ratio: float | None = None
    created_at: str
    completed_at: str | None = None


class RunProgress(BaseModel):
    """Live, process-local run progress. Ephemeral — see service/jobs.py.

    The authoritative status is always the B2 manifest; this only drives the
    UI's live progress bar while a background render is in flight.
    """

    job_id: str
    status: JobStatus
    progress: float = 0.0
    message: str | None = None
    error: str | None = None
    updated_at: str


class DashboardStats(BaseModel):
    """Dashboard metrics derived from B2 listings + manifests."""

    total_source_bytes: int
    total_source_human: str
    total_render_bytes: int
    total_render_human: str
    # The hero metric: render bytes / source bytes across all completed jobs.
    write_amplification_ratio: float
    jobs_completed: int
    jobs_total: int
    fps_minutes_processed: float


class RenderVolumePoint(BaseModel):
    """One day's rendered-output volume, for the dashboard chart."""

    date: str
    render_bytes: int


class SourceClip(BaseModel):
    """An uploaded source clip selectable in the create-job form."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    uploaded_at: str


class LibraryClip(BaseModel):
    """A source clip plus the renders derived from it (scoped library view)."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    uploaded_at: str
    renders: list["LibraryRender"] = []


class LibraryRender(BaseModel):
    """A rendered output object under renders/, tied to its source clip."""

    key: str
    multiplier: int
    size_bytes: int
    size_human: str
    status: JobStatus
    job_id: str | None = None
