"""RIFE interpolation engine — the real Practical-RIFE HDv3 model, on-device.

This is the marquee feature: genuine optical-flow neural frame interpolation
(NOT an ffmpeg minterpolate/tblend substitute). Given the frames of a source
clip, it synthesizes `multiplier - 1` intermediate frames between each adjacent
pair by recursively estimating the midpoint frame with the vendored IFNet.

Contained here in repo/ per the app's layout (heavy torch + OpenCV imports are
LAZY so the API boots and structural tests pass without the ML stack). This
module owns NO boto3 — the service downloads the clip and hands a local path in.

Device selection (deployment: local rule): auto-detect CUDA -> Apple MPS -> CPU
and DEFAULT TO CPU. Never hard-require a GPU. torch 2.6+ flips
torch.load(weights_only=True); we load the TRUSTED local checkpoint with
weights_only=False (R4).
"""

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

_model_cache: dict = {}


class RifeNotSetupError(RuntimeError):
    """Raised when the RIFE weights/model are missing or torch is unavailable.

    Callers turn this into an actionable job failure (status=failed) so the app
    keeps booting and every B2/UI flow works without the model present (R7).
    """


def weights_path() -> str:
    """Absolute path to the fetched flownet.pkl (see scripts/setup_rife.py)."""
    model_dir = settings.rife_model_dir
    if not os.path.isabs(model_dir):
        # Anchor at services/api/ — this file is services/api/app/repo/rife_engine.py,
        # so three dirname() hops (repo -> app -> api) reach the api service root.
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(base, model_dir)
    return os.path.join(model_dir, settings.rife_weights_hf_file)


def is_ready() -> bool:
    """True if the weights file exists on disk (torch presence checked at load)."""
    return os.path.exists(weights_path())


def select_device(override: str = "auto") -> str:
    """Auto-detect the inference device: cuda -> mps -> cpu. Defaults to CPU.

    Honors a non-auto override verbatim. Never raises and never requires a GPU —
    a CPU run is always a valid fallback.
    """
    if override and override != "auto":
        return override
    try:
        import torch  # type: ignore
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _load_model(device: str):
    """Load (and cache) the vendored IFNet with the pinned local weights."""
    cache_key = device
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    try:
        import torch
    except ImportError as e:
        raise RifeNotSetupError(
            "torch is not installed — run: pip install -r requirements-ml.txt"
        ) from e

    path = weights_path()
    if not os.path.exists(path):
        raise RifeNotSetupError(
            "RIFE model not set up — run scripts/setup_rife.py (pnpm setup:rife)"
        )

    from app.repo.rife_vendor.ifnet_hdv3 import IFNet

    net = IFNet()
    # R4: the checkpoint is a TRUSTED local file we fetched from a pinned
    # mirror, so weights_only=False is safe here (and required — flownet.pkl
    # carries non-tensor globals torch 2.6+ would otherwise reject).
    state = torch.load(path, map_location="cpu", weights_only=False)
    if hasattr(state, "state_dict"):
        state = state.state_dict()
    state = {(k[7:] if k.startswith("module.") else k): v for k, v in state.items()}
    net.load_state_dict(state, strict=True)
    net.eval()
    net.to(torch.device(device))
    _model_cache[cache_key] = net
    logger.info("Loaded RIFE HDv3 model on device=%s", device)
    return net


def _pad_dims(h: int, w: int, factor: int = 16) -> tuple[int, int]:
    """IFNet needs H/W divisible by 16 (three /2 downsamples in the blocks)."""
    return ((h + factor - 1) // factor) * factor, ((w + factor - 1) // factor) * factor


def interpolate_frames(frames, multiplier: int, device: str):
    """Yield the interpolated frame sequence for a list of RGB frames.

    frames: list of HxWx3 uint8 BGR numpy arrays (OpenCV order).
    Recursively estimates midpoints so 2x inserts 1, 4x inserts 3, 8x inserts 7
    frames between each adjacent source pair. Genuine flow-warp interpolation.

    Returns a list of HxWx3 uint8 BGR frames (length ~= (n-1)*multiplier + 1).
    """
    import numpy as np
    import torch

    net = _load_model(device)
    dev = torch.device(device)

    def to_tensor(bgr):
        rgb = bgr[:, :, ::-1].copy()
        t = torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        return t.to(dev)

    def to_bgr(t):
        arr = (t.clamp(0, 1)[0].permute(1, 2, 0).cpu().numpy() * 255.0).round().astype(np.uint8)
        return arr[:, :, ::-1].copy()

    def midpoint(t0, t1):
        h, w = t0.shape[2], t0.shape[3]
        ph, pw = _pad_dims(h, w)
        pad = (0, pw - w, 0, ph - h)
        a = torch.nn.functional.pad(t0, pad)
        b = torch.nn.functional.pad(t1, pad)
        with torch.no_grad():
            _, _, mid = net(torch.cat((a, b), 1), scale_list=(4, 2, 1))
        return mid[:, :, :h, :w]

    def between(t0, t1, steps):
        """Return `steps - 1` interpolated tensors strictly between t0 and t1."""
        if steps <= 1:
            return []
        mid = midpoint(t0, t1)
        if steps == 2:
            return [mid]
        left = between(t0, mid, steps // 2)
        right = between(mid, t1, steps - steps // 2)
        return [*left, mid, *right]

    tensors = [to_tensor(f) for f in frames]
    out: list = []
    for i in range(len(tensors) - 1):
        out.append(to_bgr(tensors[i]))
        for mt in between(tensors[i], tensors[i + 1], multiplier):
            out.append(to_bgr(mt))
    if tensors:
        out.append(to_bgr(tensors[-1]))
    return out
