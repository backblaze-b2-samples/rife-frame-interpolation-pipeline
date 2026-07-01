"""Video decode + encode adapter for the interpolation pipeline.

- decode_frames(path)  -> read a source clip's frames (OpenCV) + probe its fps.
- encode_frames(...)   -> pipe interpolated frames to the BUNDLED ffmpeg binary
                          and write a browser-playable render.

R5: the default codec is H.264 (libx264) in MP4 with yuv420p + faststart so
renders actually paint in the <video> element. H.265/HEVC (libx265) is an
opt-in choice that may not play in Chrome — kept as a codec option, not the
default (a deliberate deviation from the "MP4/H.265" wording, justified by
browser playability).

R6: the encoder is resolved via imageio_ffmpeg.get_ffmpeg_exe() — NOT bare
Homebrew ffmpeg (which may ship slim). Heavy imports (cv2, imageio_ffmpeg) are
lazy so this module is importable for structural tests without the ML stack.
This module owns NO boto3 — the service hands it local paths.
"""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

# libx264/libx265 both require even width/height with yuv420p.
_CODEC_ARGS = {
    "h264": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18"],
    "h265": ["-c:v", "libx265", "-pix_fmt", "yuv420p", "-crf", "22",
             "-tag:v", "hvc1"],
}


def _even(n: int) -> int:
    return n if n % 2 == 0 else n - 1


def decode_frames(path: str, max_frames: int) -> dict:
    """Decode up to `max_frames` frames from a clip; return frames + source fps.

    Returns {"frames": [HxWx3 uint8 BGR, ...], "fps": float, "width", "height"}.
    """
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source clip: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames: list = []
    try:
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        cap.release()
    if not frames:
        raise RuntimeError(f"No decodable frames in source clip: {path}")
    h, w = frames[0].shape[:2]
    return {"frames": frames, "fps": float(fps), "width": w, "height": h}


def encode_frames(
    frames: list,
    out_path: str,
    fps: float,
    codec: str = "h264",
) -> None:
    """Encode BGR frames to a browser-playable render via the bundled ffmpeg.

    Raises RuntimeError on encode failure. Frames are cropped to even
    dimensions (libx264/libx265 + yuv420p requirement).
    """
    import cv2  # noqa: F401  (frames come pre-decoded; kept for symmetry)
    import imageio_ffmpeg

    if not frames:
        raise RuntimeError("No frames to encode")

    h, w = frames[0].shape[:2]
    ew, eh = _even(w), _even(h)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    codec_args = _CODEC_ARGS.get(codec, _CODEC_ARGS["h264"])
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{ew}x{eh}",
        "-r", f"{max(1.0, fps):.3f}",
        "-i", "pipe:0",
        "-an",
        *codec_args,
        "-movflags", "+faststart",
        out_path,
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    try:
        for frame in frames:
            crop = frame[:eh, :ew]
            proc.stdin.write(crop.tobytes())
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        stderr = proc.stderr.read() if proc.stderr else b""
        proc.wait()

    if proc.returncode != 0:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise RuntimeError(f"ffmpeg encode failed: {(stderr or b'')[-400:]!r}")
