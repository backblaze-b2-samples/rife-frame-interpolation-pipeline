"""Video clip metadata extraction.

This app deals in VIDEO CLIPS only (the input to a RIFE interpolation job), so
metadata extraction is narrowed to video: duration, fps, codec, resolution and
bitrate. fps in particular is load-bearing — the pipeline multiplies it to
compute the target frame rate and the write-amplification ratio.

The heavy `imageio-ffmpeg` probe import is lazy so this module (and the upload
path) stays importable without the ML stack; if probing is unavailable the
core hashes/size still return and video fields are simply left null.
"""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def _ffprobe_video(file_data: bytes, extension: str) -> dict:
    """Probe a video clip for fps/duration/codec/resolution/bitrate.

    Uses the ffprobe that ships alongside the bundled imageio-ffmpeg binary so
    there is no reliance on a system ffmpeg. Returns {} on any failure — video
    metadata is best-effort and must never block an upload.
    """
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # ffprobe lives next to the bundled ffmpeg; fall back to system ffprobe.
        ffprobe = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe")
        if not os.path.exists(ffprobe):
            ffprobe = "ffprobe"

        fd, tmp = tempfile.mkstemp(suffix=f".{extension or 'mp4'}")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(file_data)
            out = subprocess.run(
                [
                    ffprobe, "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries",
                    "stream=avg_frame_rate,codec_name,width,height:format=duration,bit_rate",
                    "-of", "json", tmp,
                ],
                capture_output=True, text=True, timeout=30,
            )
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        if out.returncode != 0:
            return {}
        data = json.loads(out.stdout or "{}")
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        return {
            "fps": _parse_fps(stream.get("avg_frame_rate")),
            "codec": stream.get("codec_name"),
            "video_width": _int_or_none(stream.get("width")),
            "video_height": _int_or_none(stream.get("height")),
            "duration_seconds": _float_or_none(fmt.get("duration")),
            "bitrate": _int_or_none(fmt.get("bit_rate")),
        }
    except Exception:
        logger.warning("Video metadata extraction failed", exc_info=True)
        return {}


def _parse_fps(raw: str | None) -> float | None:
    """ffprobe reports frame rate as a 'num/den' rational (e.g. '24000/1001')."""
    if not raw or raw == "0/0":
        return None
    try:
        num, _, den = raw.partition("/")
        d = float(den) if den else 1.0
        return round(float(num) / d, 3) if d else None
    except (ValueError, ZeroDivisionError):
        return None


def _int_or_none(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _float_or_none(v) -> float | None:
    try:
        return round(float(v), 3) if v is not None else None
    except (ValueError, TypeError):
        return None


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}
    if content_type.startswith("video/"):
        extra = _ffprobe_video(file_data, extension)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
        **extra,
    )
