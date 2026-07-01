"""Scoped media library — this app's own source clips + their renders.

Distinct from the full-bucket /files explorer: the library is scoped to the
app's two prefixes only (source/clips/ and renders/). It pairs each source clip
with the renders derived from it (by clip_id) for inline playback.

No boto3 — everything via the repo.
"""

import logging
import os

from app.config import settings
from app.repo import get_json, list_files
from app.service.jobs import clip_id_for, manifest_key
from app.types import InterpolationJob, LibraryClip, LibraryRender
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def _renders_for(clip_id: str) -> list[LibraryRender]:
    """Return the renders that exist for a clip id, keyed off job manifests."""
    out: list[LibraryRender] = []
    for f in list_files(prefix=f"{settings.render_prefix}{clip_id}/", max_keys=1000):
        if not f.key.endswith(".mp4"):
            continue
        # renders/<clip_id>/<mult>x/render.mp4 -> parse the multiplier segment.
        parts = f.key.split("/")
        mult_seg = parts[2] if len(parts) > 2 else "0x"
        try:
            multiplier = int(mult_seg.rstrip("x"))
        except ValueError:
            multiplier = 0
        manifest = get_json(manifest_key(clip_id, multiplier))
        job = InterpolationJob(**manifest) if manifest else None
        out.append(
            LibraryRender(
                key=f.key,
                multiplier=multiplier,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                status=job.status if job else "completed",
                job_id=job.job_id if job else None,
            )
        )
    out.sort(key=lambda r: r.multiplier)
    return out


def list_library() -> list[LibraryClip]:
    """List source clips paired with their derived renders (newest clip first)."""
    clips: list[LibraryClip] = []
    for f in list_files(prefix=settings.source_prefix, max_keys=1000):
        if f.key.endswith("/"):
            continue
        clip_id = clip_id_for(f.key)
        clips.append(
            LibraryClip(
                key=f.key,
                filename=os.path.basename(f.key),
                size_bytes=f.size_bytes,
                size_human=humanize_bytes(f.size_bytes),
                uploaded_at=f.uploaded_at.isoformat(),
                renders=_renders_for(clip_id),
            )
        )
    clips.sort(key=lambda c: c.uploaded_at, reverse=True)
    return clips
