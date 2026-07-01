"""Interpolation-job CRUD + dashboard aggregations, all derived from B2.

The job registry is the renders/ prefix on B2: each job is a
renders/<clip_id>/<multiplier>/manifest.json. There is no application DB — the
manifest is authoritative. Dashboard stats roll up the same manifests + bucket
listings.

No boto3 — everything goes through the repo. The RIFE model + encode live in
repo/ (rife_engine, encoder) and are driven by service/interpolation.py, not
here.
"""

import logging
import os
import re
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import get_json, list_files, list_keys, put_json
from app.service.files import validate_key
from app.types import (
    InterpolationJob,
    JobConfig,
    JobSummary,
    SourceClip,
)

logger = logging.getLogger(__name__)


class JobNotFound(Exception):
    """Raised when a job id has no manifest."""


class ClipNotFound(Exception):
    """Raised when the create form references a source clip that doesn't exist."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def clip_id_for(source_key: str) -> str:
    """Stable, filesystem-safe id derived from a source clip's object key."""
    base = os.path.splitext(os.path.basename(source_key))[0]
    return re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_") or "clip"


def manifest_key(clip_id: str, multiplier: int) -> str:
    return f"{settings.render_prefix}{clip_id}/{multiplier}x/manifest.json"


def render_key(clip_id: str, multiplier: int, codec: str) -> str:
    # Both H.264 and HEVC are muxed into an .mp4 container (HEVC uses hvc1 tag).
    return f"{settings.render_prefix}{clip_id}/{multiplier}x/render.mp4"


def job_prefix(clip_id: str, multiplier: int) -> str:
    return f"{settings.render_prefix}{clip_id}/{multiplier}x/"


def list_source_clips() -> list[SourceClip]:
    """List uploaded source clips selectable in the create-job form."""
    out: list[SourceClip] = []
    for f in list_files(prefix=settings.source_prefix, max_keys=1000):
        if f.key.endswith("/"):
            continue
        out.append(
            SourceClip(
                key=f.key,
                filename=f.filename,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at.isoformat(),
            )
        )
    return out


def _manifest_keys() -> list[str]:
    """Return every job manifest key present under the render prefix."""
    return [
        k for k in list_keys(prefix=settings.render_prefix, max_keys=1000)
        if k.endswith("/manifest.json")
    ]


def _source_filename(source_key: str) -> str:
    return os.path.basename(source_key)


def list_jobs() -> list[JobSummary]:
    """List all jobs as lightweight summaries (newest first)."""
    summaries: list[JobSummary] = []
    for mk in _manifest_keys():
        obj = get_json(mk)
        if not obj:
            continue
        job = InterpolationJob(**obj)
        summaries.append(
            JobSummary(
                job_id=job.job_id,
                source_key=job.config.source_key,
                source_filename=_source_filename(job.config.source_key),
                multiplier=job.config.multiplier,
                codec=job.config.codec,
                status=job.status,
                source_bytes=job.source_bytes,
                render_bytes=job.render_bytes,
                amplification_ratio=job.amplification_ratio,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def get_job(clip_id: str, multiplier: int) -> InterpolationJob:
    """Fetch a job manifest. Raises JobNotFound if absent."""
    obj = get_json(manifest_key(clip_id, multiplier))
    if obj is None:
        raise JobNotFound(f"{clip_id}/{multiplier}x")
    return InterpolationJob(**obj)


def create_job(config: JobConfig) -> InterpolationJob:
    """Create a new PENDING job manifest in B2 for a (clip, multiplier, codec)."""
    validate_key(config.source_key)
    # Confirm the source clip actually exists before minting a job.
    clips = {c.key for c in list_source_clips()}
    if config.source_key not in clips:
        raise ClipNotFound(config.source_key)

    clip_id = clip_id_for(config.source_key)
    job = InterpolationJob(
        job_id=uuid.uuid4().hex[:12],
        config=config,
        status="pending",
        created_at=_now(),
    )
    put_json(manifest_key(clip_id, config.multiplier), job.model_dump())
    logger.info(
        "Created job clip=%s mult=%dx codec=%s", clip_id, config.multiplier, config.codec
    )
    return job


def save_job(clip_id: str, job: InterpolationJob) -> None:
    """Persist a job manifest (used by the run orchestration)."""
    put_json(manifest_key(clip_id, job.config.multiplier), job.model_dump())


def delete_job(clip_id: str, multiplier: int) -> int:
    """Delete a job's manifest + its render, SCOPED to its own prefix."""
    # Confirm it exists (raises if not) so callers get a clean 404.
    get_job(clip_id, multiplier)
    from app.repo import delete_prefix

    prefix = job_prefix(clip_id, multiplier)
    deleted = delete_prefix(prefix)
    logger.info("Deleted job clip=%s mult=%dx objects=%d", clip_id, multiplier, deleted)
    return deleted
