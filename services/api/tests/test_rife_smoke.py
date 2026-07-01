"""Real (un-mocked) RIFE smoke — skipped unless the ML stack + weights exist.

This is the end-to-end reproducibility guard (R2): it loads the vendored HDv3
arch with the fetched weights and confirms it interpolates a genuine midpoint
frame on CPU (differs from a naive average -> real optical-flow warp). It never
runs in a bare `pnpm test:api` (no torch), so CI stays fast; run it locally after
`pnpm setup:rife` to prove the arch+weights pair actually works.
"""

import importlib.util

import pytest

_HAS_TORCH = importlib.util.find_spec("torch") is not None


@pytest.mark.skipif(not _HAS_TORCH, reason="torch not installed (requirements-ml.txt)")
def test_rife_interpolates_midpoint_on_cpu():
    import numpy as np

    from app.repo import rife_engine

    if not rife_engine.is_ready():
        pytest.skip("RIFE weights not fetched — run scripts/setup_rife.py")

    # Two distinct frames with horizontal motion.
    h, w = 64, 96
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[:, : w // 2] = 255
    b = np.zeros((h, w, 3), dtype=np.uint8)
    b[:, w // 2 :] = 255

    out = rife_engine.interpolate_frames([a, b], multiplier=2, device="cpu")
    # 2x of a 2-frame clip => first, one midpoint, last.
    assert len(out) == 3
    mid = out[1].astype(np.float32)
    avg = ((a.astype(np.float32) + b.astype(np.float32)) / 2)
    assert mid.shape == (h, w, 3)
    # A real flow-warped midpoint is NOT a pixel average.
    assert float(np.abs(mid - avg).mean()) > 1.0
