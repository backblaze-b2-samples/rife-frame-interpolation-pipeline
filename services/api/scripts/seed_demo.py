#!/usr/bin/env python
"""Seed a short synthetic source clip into B2 so a fresh clone has something to
interpolate — WITHOUT committing any binary asset (R12).

Generates a ~2s, 24 fps, small-resolution clip with the BUNDLED ffmpeg
(imageio-ffmpeg) test sources (testsrc2 + a moving box) and uploads it to
source/clips/ over the S3 API. Requires B2 credentials in .env and the ML
extras (imageio-ffmpeg) installed.

Usage:
    cd services/api && source .venv/bin/activate
    python scripts/seed_demo.py
"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.repo import upload_file


def _generate_clip(path: str) -> None:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # testsrc2 has genuine motion (a sweeping bar) so interpolation has real
    # optical flow to work with — not a static frame.
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", "testsrc2=size=320x180:rate=24:duration=2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffmpeg clip generation failed: {out.stderr[-400:]}")


def main() -> int:
    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        print(
            "imageio-ffmpeg is not installed. Run:\n  pip install -r requirements-ml.txt",
            file=sys.stderr,
        )
        return 1

    if not settings.b2_application_key_id or not settings.b2_bucket_name:
        print("B2 credentials are not configured in .env — see .env.example.", file=sys.stderr)
        return 1

    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        print("Generating a 2s 24fps synthetic clip with the bundled ffmpeg ...")
        _generate_clip(path)
        with open(path, "rb") as f:
            data = f.read()
        key = f"{settings.source_prefix}demo-testsrc-24fps.mp4"
        result = upload_file(data, key, "video/mp4")
        print(f"Uploaded demo clip to b2://{settings.b2_bucket_name}/{result.key} ({result.size_human})")
        print("Now create a render job for it at /jobs (New render job).")
    finally:
        if os.path.exists(path):
            os.unlink(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
