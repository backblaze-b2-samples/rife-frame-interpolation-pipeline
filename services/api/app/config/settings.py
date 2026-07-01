from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (Standard #3 env var names) ---
    # Region drives the S3 endpoint; we never store the full endpoint URL,
    # so there is no hardcoded region string anywhere in source.
    b2_region: str = "us-west-004"
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits — source clips can be large.
    max_file_size: int = 500 * 1024 * 1024  # 500MB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- Frame-interpolation pipeline ---
    # Uploaded source clips land here; the job create form and the dashboard
    # both list this prefix to find clips.
    source_prefix: str = "source/clips/"
    # Rendered slow-motion output (+ per-job manifests) lives here, isolated
    # per clip + multiplier: renders/<clip_id>/<multiplier>/.
    render_prefix: str = "renders/"

    # --- RIFE model (Practical-RIFE HDv3, run on-device) ---
    # Weights are fetched by scripts/setup_rife.py from a PINNED HuggingFace
    # mirror into RIFE_MODEL_DIR (gitignored). Repo/file/revision are all
    # env-configurable so you can swap in your own mirror; the defaults are a
    # verified, working HDv3 arch+weights pair (MIT, credit hzwer/Practical-RIFE).
    rife_model_dir: str = "models/rife"
    rife_weights_hf_repo: str = "AlexWortega/RIFE"
    rife_weights_hf_file: str = "flownet.pkl"
    rife_weights_hf_revision: str = "440cdec905de98e1d7e81f65d2c88a08da7cb4e2"

    # Device is auto-detected at runtime (CUDA -> Apple MPS -> CPU) and
    # defaults to CPU. "auto" lets the engine pick; set "cpu"/"cuda"/"mps"
    # to force a device. Never hard-requires a GPU.
    device: str = "auto"

    # Caps a CPU demo so a render finishes fast. Source frames beyond this are
    # truncated before interpolation; raise it for a full clip.
    max_source_frames: int = 240

    # Default render codec. H.264 (libx264/MP4, yuv420p, +faststart) is the
    # browser-playable default; "h265" (HEVC) is an opt-in choice that may not
    # play in Chrome. See docs — deliberate deviation for playability.
    default_codec: str = "h264"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def b2_endpoint(self) -> str:
        """Derive the S3-compatible endpoint from the region.

        Keeping only the region in config means no hardcoded endpoint /
        region string lives anywhere else in the source tree.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"


settings = Settings()
