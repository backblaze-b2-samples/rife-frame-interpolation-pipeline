"""Engine + interpolation-orchestration tests that run WITHOUT the ML stack.

These guard the lazy-import contract (importing the engine / service must not
pull torch / cv2 / imageio_ffmpeg) and the run wiring (R9): the orchestration is
exercised with a MOCKED engine + encoder so CI catches drift without any weight
download or torch run. A real un-mocked smoke lives in test_rife_smoke.py and is
skipped unless the ML stack + weights are present.
"""

import builtins
import sys


def test_engine_imports_without_ml_stack():
    """Importing the engine + orchestration must not import the heavy deps."""
    import app.repo.encoder
    import app.repo.rife_engine  # noqa: F401
    from app.service import interpolation  # noqa: F401

    for heavy in ("torch", "cv2", "imageio_ffmpeg", "numpy"):
        assert heavy not in sys.modules, f"{heavy} was eagerly imported"


def test_device_defaults_to_cpu_without_torch(monkeypatch):
    """With torch absent, device selection reports CPU (never require a GPU)."""
    real_import = builtins.__import__

    def _no_torch(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise ImportError("torch absent (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", _no_torch)

    from app.repo.rife_engine import select_device

    assert select_device("auto") == "cpu"


def test_device_auto_returns_valid_device():
    from app.repo.rife_engine import select_device

    assert select_device("auto") in {"cpu", "cuda", "mps"}


def test_device_honors_explicit_override():
    from app.repo.rife_engine import select_device

    assert select_device("cuda") == "cuda"
    assert select_device("mps") == "mps"


def test_clip_id_is_filesystem_safe():
    from app.service.jobs import clip_id_for

    assert clip_id_for("source/clips/Highway Clip 01.mov") == "Highway_Clip_01"
    assert clip_id_for("source/clips/slow-mo.mp4") == "slow-mo"


def test_render_and_manifest_keys_are_scoped():
    from app.service.jobs import job_prefix, manifest_key, render_key

    assert manifest_key("clipA", 4) == "renders/clipA/4x/manifest.json"
    assert render_key("clipA", 4, "h264") == "renders/clipA/4x/render.mp4"
    assert job_prefix("clipA", 4) == "renders/clipA/4x/"


def test_run_interpolation_wiring_with_mocked_engine(monkeypatch):
    """R9: exercise download -> decode -> interpolate -> encode -> upload ->
    manifest with EVERY external call mocked (no B2, no torch, no ffmpeg).

    Verifies the orchestration computes the amplification ratio and persists a
    completed manifest — the wiring CI must protect without the model.
    """
    from app.service import interpolation, jobs, progress
    from app.types import InterpolationJob, JobConfig

    saved = {}
    # Frames are opaque sentinels here — the engine + encoder are mocked, so the
    # wiring test needs NO numpy / torch / ffmpeg (that is the whole point).
    frame = object()

    def _touch(path):
        with open(path, "wb"):
            pass

    monkeypatch.setattr(interpolation, "download_to_file", lambda key, path: _touch(path))
    monkeypatch.setattr(interpolation, "head_size", lambda key: 1000)
    monkeypatch.setattr(interpolation, "multipart_upload_file", lambda path, key, ct: 4000)

    encoded = {}

    class _Encoder:
        @staticmethod
        def decode_frames(path, maxf):
            return {"frames": [frame, frame, frame], "fps": 24.0, "width": 16, "height": 16}

        @staticmethod
        def encode_frames(frames, out_path, fps, codec):
            encoded.update({"fps": fps, "n_frames": len(frames)})
            _touch(out_path)

    class _Engine:
        @staticmethod
        def select_device(override):
            return "cpu"

        @staticmethod
        def interpolate_frames(frames, mult, device):
            return frames * mult  # more frames out than in

        RifeNotSetupError = interpolation.RifeNotSetupError

    # run_interpolation does `from app.repo import encoder, rife_engine` — bind
    # our stubs as attributes on the app.repo package so that resolves to them.
    import app.repo as repo_pkg

    monkeypatch.setattr(repo_pkg, "encoder", _Encoder, raising=False)
    monkeypatch.setattr(repo_pkg, "rife_engine", _Engine, raising=False)
    monkeypatch.setattr(jobs, "save_job", lambda clip_id, job: saved.update({clip_id: job}))
    monkeypatch.setattr(progress, "start", lambda job_id: None)
    monkeypatch.setattr(progress, "update", lambda *a, **k: None)

    job = InterpolationJob(
        job_id="test123",
        config=JobConfig(source_key="source/clips/x.mp4", multiplier=4, codec="h264"),
        created_at="2026-02-14T00:00:00Z",
    )
    result = interpolation.run_interpolation(job)

    assert result.status == "completed"
    assert result.source_bytes == 1000
    assert result.render_bytes == 4000
    assert result.amplification_ratio == 4.0
    assert result.source_fps == 24.0
    # Slow motion: the render is encoded at the SOURCE fps, not source*mult, so
    # the extra frames stretch the clip to 4x its duration (1/4 speed). Encoding
    # at 96 fps here would keep the duration and only smooth it (an fps boost).
    assert encoded["fps"] == 24.0
    assert encoded["n_frames"] == 12  # 3 frames * 4x mult (mocked engine)
    assert result.render_key == "renders/x/4x/render.mp4"
    assert "x" in saved
