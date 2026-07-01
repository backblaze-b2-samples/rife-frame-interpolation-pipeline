"""Jobs router: interpolation-job CRUD, run with live progress, dashboard.

Thin HTTP layer — validation + status mapping only. All work flows through the
service layer (jobs / interpolation / dashboard / progress); no boto3, no ML
imports here.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service import progress
from app.service.dashboard import get_dashboard_stats, get_render_volume
from app.service.files import FileKeyError, get_preview_url
from app.service.interpolation import run_job
from app.service.jobs import (
    ClipNotFound,
    JobNotFound,
    create_job,
    delete_job,
    get_job,
    list_jobs,
    list_source_clips,
)
from app.types import (
    DashboardStats,
    InterpolationJob,
    JobConfig,
    JobSummary,
    RenderVolumePoint,
    RunProgress,
    SourceClip,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs/sources", response_model=list[SourceClip])
async def list_sources_endpoint():
    return list_source_clips()


@router.get("/jobs/stats", response_model=DashboardStats)
async def dashboard_stats_endpoint():
    return get_dashboard_stats()


@router.get("/jobs/stats/volume", response_model=list[RenderVolumePoint])
async def render_volume_endpoint(days: int = 14):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_render_volume(days=days)


@router.get("/jobs/progress", response_model=list[RunProgress])
async def list_progress_endpoint():
    return progress.list_runs()


@router.get("/jobs", response_model=list[JobSummary])
async def list_jobs_endpoint():
    return list_jobs()


@router.post("/jobs", response_model=InterpolationJob)
async def create_job_endpoint(payload: dict):
    config_data = (payload or {}).get("config") or payload or {}
    try:
        config = JobConfig(**config_data)
        return create_job(config)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ClipNotFound as e:
        raise HTTPException(status_code=400, detail=f"Source clip not found: {e}") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/jobs/{clip_id}/{multiplier}", response_model=InterpolationJob)
async def get_job_endpoint(clip_id: str, multiplier: int):
    try:
        return get_job(clip_id, multiplier)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="Job not found") from None


@router.delete("/jobs/{clip_id}/{multiplier}")
async def delete_job_endpoint(clip_id: str, multiplier: int):
    try:
        deleted = delete_job(clip_id, multiplier)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="Job not found") from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete job") from None
    return {"deleted": True, "clip_id": clip_id, "multiplier": multiplier, "objects": deleted}


@router.post("/jobs/{clip_id}/{multiplier}/run", response_model=RunProgress)
async def run_job_endpoint(
    clip_id: str, multiplier: int, background_tasks: BackgroundTasks
):
    try:
        job = get_job(clip_id, multiplier)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="Job not found") from None

    if progress.active(job.job_id):
        run = progress.get(job.job_id)
        if run is not None:
            return run

    run = progress.start(job.job_id)
    background_tasks.add_task(run_job, clip_id, job)
    logger.info("Enqueued render job=%s clip=%s mult=%dx", job.job_id, clip_id, multiplier)
    return run


@router.get("/jobs/{clip_id}/{multiplier}/render")
async def render_url_endpoint(clip_id: str, multiplier: int):
    """Presigned URL for in-browser playback of the rendered slow-mo output."""
    try:
        job = get_job(clip_id, multiplier)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="Job not found") from None
    if not job.render_key:
        raise HTTPException(status_code=404, detail="Render not available yet")
    try:
        return {"url": get_preview_url(job.render_key)}
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
