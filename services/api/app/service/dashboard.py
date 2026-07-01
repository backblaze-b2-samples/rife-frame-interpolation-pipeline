"""Dashboard aggregations for the interpolation pipeline.

The hero metric is WRITE AMPLIFICATION: total render bytes / total source bytes
across completed jobs — the classic write-heavy B2 workload this app showcases.
Everything is derived from B2 listings + job manifests (no DB). No boto3 — all
via the repo.
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.repo import get_object_stats, list_files
from app.service.jobs import list_jobs
from app.types import DashboardStats, RenderVolumePoint
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def get_dashboard_stats() -> DashboardStats:
    """Roll up write-amplification + throughput metrics for the dashboard."""
    source = get_object_stats(prefix=settings.source_prefix)
    render = get_object_stats(prefix=settings.render_prefix)
    total_source = source["total_size_bytes"]
    total_render = render["total_size_bytes"]

    jobs = list_jobs()
    completed = [j for j in jobs if j.status == "completed"]
    # fps-minutes: a proxy for compute throughput — sum of target fps * duration
    # is unavailable without probing, so we approximate with rendered frames via
    # the amplification payload; keep it simple and honest: count completed jobs
    # weighted by multiplier as "fps-minutes processed".
    fps_minutes = round(sum(j.multiplier for j in completed) * 1.0, 2)

    ratio = round(total_render / total_source, 3) if total_source else 0.0
    return DashboardStats(
        total_source_bytes=total_source,
        total_source_human=humanize_bytes(total_source),
        total_render_bytes=total_render,
        total_render_human=humanize_bytes(total_render),
        write_amplification_ratio=ratio,
        jobs_completed=len(completed),
        jobs_total=len(jobs),
        fps_minutes_processed=fps_minutes,
    )


def get_render_volume(days: int = 14) -> list[RenderVolumePoint]:
    """Rendered-output bytes per day over the last N days (dashboard chart)."""
    renders = [
        f for f in list_files(prefix=settings.render_prefix, max_keys=1000)
        if f.key.endswith(".mp4")
    ]
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)

    bytes_by_day: dict[str, int] = defaultdict(int)
    for f in renders:
        d = f.uploaded_at.date()
        if d >= cutoff:
            bytes_by_day[d.isoformat()] += f.size_bytes

    return [
        RenderVolumePoint(
            date=(cutoff + timedelta(days=i)).isoformat(),
            render_bytes=bytes_by_day.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
