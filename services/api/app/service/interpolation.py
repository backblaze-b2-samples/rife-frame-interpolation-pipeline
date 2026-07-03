"""Interpolation run orchestration: source clip -> smooth slow-motion render.

Flow (the write-amplification story — a 4x render of a 1 TB library makes 4+ TB):

    source/clips/<clip>  --download-->  decode frames (OpenCV) -->
        RIFE HDv3 neural interpolation (multiplier-1 synthesized frames per pair)
        --> re-encode to browser-playable MP4 (H.264 default) at the SOURCE fps,
            so the ~multiplier-more frames stretch the timeline into genuine
            slow motion (duration x multiplier, playback 1/multiplier speed) --
            NOT an fps boost, which would keep the duration and only smooth it
        --> MULTIPART upload to renders/<clip_id>/<multiplier>x/render.mp4
        --> update renders/<clip_id>/<multiplier>x/manifest.json (status, sizes,
            amplification_ratio)

This module owns NO boto3 — it calls the repo for all B2 I/O, the RIFE engine
for interpolation, and the encoder for decode/encode. Heavy ML imports stay in
repo/rife_engine.py + repo/encoder.py (lazy), so importing this module is cheap.
Runs execute in a FastAPI BackgroundTask thread; live progress goes to the
ephemeral progress registry, the manifest in B2 is authoritative (R7).
"""

import logging
import os
import tempfile
from datetime import UTC, datetime

from app.config import settings
from app.repo import download_to_file, head_size, multipart_upload_file
from app.repo.rife_engine import RifeNotSetupError
from app.service import jobs, progress
from app.types import InterpolationJob

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fail(clip_id: str, job: InterpolationJob, message: str) -> None:
    """Record an actionable failure on the run + manifest (R7)."""
    failed = job.model_copy(
        update={"status": "failed", "error": message, "completed_at": _now()}
    )
    progress.update(job.job_id, status="failed", error=message)
    try:
        jobs.save_job(clip_id, failed)
    except Exception:  # best effort — the run already carries the error
        logger.exception("Failed to persist error manifest: %s", clip_id)


def run_interpolation(job: InterpolationJob) -> InterpolationJob:
    """Execute one render end-to-end. Persists artifacts + manifest to B2.

    Returns the updated manifest. On a recoverable setup problem (model absent,
    torch missing) raises RifeNotSetupError with an actionable message; the
    caller turns any failure into status=failed so the app keeps working (R7).
    """
    from app.repo import encoder, rife_engine

    cfg = job.config
    clip_id = jobs.clip_id_for(cfg.source_key)
    progress.start(job.job_id)
    progress.update(job.job_id, progress=0.05, message="Downloading source clip")

    source_bytes = head_size(cfg.source_key) or 0
    fd, src_path = tempfile.mkstemp(suffix=os.path.splitext(cfg.source_key)[1] or ".mp4")
    os.close(fd)
    out_fd, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(out_fd)
    try:
        download_to_file(cfg.source_key, src_path)

        progress.update(job.job_id, progress=0.15, message="Decoding source frames")
        decoded = encoder.decode_frames(src_path, settings.max_source_frames)
        source_fps = decoded["fps"]
        # Slow motion: the interpolated frames play back at the SOURCE fps, so
        # the extra frames stretch the clip to multiplier x its duration (speed
        # = 1/multiplier). Encoding at source_fps*multiplier would instead keep
        # the duration and merely raise smoothness -- an fps boost, not slow-mo.
        speed_factor = 1.0 / cfg.multiplier

        device = rife_engine.select_device(settings.device)
        progress.update(
            job.job_id, progress=0.25,
            message=f"Interpolating {cfg.multiplier}x on {device} ({len(decoded['frames'])} frames)",
        )
        frames = rife_engine.interpolate_frames(
            decoded["frames"], cfg.multiplier, device
        )

        progress.update(job.job_id, progress=0.75, message="Encoding render (H.264)")
        encoder.encode_frames(frames, out_path, fps=source_fps, codec=cfg.codec)

        progress.update(job.job_id, progress=0.9, message="Uploading render to B2 (multipart)")
        rkey = jobs.render_key(clip_id, cfg.multiplier, cfg.codec)
        render_bytes = multipart_upload_file(out_path, rkey, "video/mp4")

        ratio = round(render_bytes / source_bytes, 3) if source_bytes else None
        completed = job.model_copy(
            update={
                "status": "completed",
                "source_fps": round(source_fps, 3),
                "source_bytes": source_bytes,
                "render_bytes": render_bytes,
                "amplification_ratio": ratio,
                "render_key": rkey,
                "error": None,
                "completed_at": _now(),
            }
        )
        jobs.save_job(clip_id, completed)
        progress.update(
            job.job_id, status="completed", progress=1.0,
            message=(
                f"Rendered {cfg.multiplier}x slow motion "
                f"({speed_factor:g}x speed at {source_fps:g} fps, "
                f"{ratio}x write amplification)"
            ),
        )
        logger.info(
            "Rendered clip=%s mult=%dx speed=%.3gx fps=%.3g frames=%d "
            "src=%dB render=%dB ratio=%s",
            clip_id, cfg.multiplier, speed_factor, source_fps, len(frames),
            source_bytes, render_bytes, ratio,
        )
        return completed
    finally:
        for p in (src_path, out_path):
            if os.path.exists(p):
                os.unlink(p)


def run_job(clip_id: str, job: InterpolationJob) -> None:
    """Background entrypoint: run a render, recording errors on run + manifest."""
    try:
        run_interpolation(job)
    except RifeNotSetupError as e:
        logger.warning("Job blocked (model not set up): %s", e)
        _fail(clip_id, job, str(e))
    except Exception as e:  # surface any failure on the run + manifest
        logger.exception("Interpolation job failed: clip=%s", clip_id)
        _fail(clip_id, job, str(e))
