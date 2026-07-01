#!/usr/bin/env python
"""Fetch the RIFE model weights from a pinned, reproducible HuggingFace mirror.

Upstream Practical-RIFE distributes `flownet.pkl` only via Google Drive / Baidu,
which cannot be used for automated / clean-install setup (R2). This script pulls
the SAME weights from a PINNED HuggingFace mirror revision so `pnpm setup:rife`
is deterministic and scriptable.

The repo / file / revision are all env-configurable (RIFE_WEIGHTS_HF_REPO,
RIFE_WEIGHTS_HF_FILE, RIFE_WEIGHTS_HF_REVISION, RIFE_MODEL_DIR) — the defaults
are a verified HDv3 arch+weights pair (MIT; credit hzwer/Practical-RIFE) whose
160-tensor state dict loads into app/repo/rife_vendor/ifnet_hdv3.py with
strict=True.

Usage:
    cd services/api && source .venv/bin/activate
    python scripts/setup_rife.py
"""

import os
import shutil
import sys

# Make the app package importable so we reuse the single source of config.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings


def _model_dir() -> str:
    d = settings.rife_model_dir
    if not os.path.isabs(d):
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), d)
    return d


def main() -> int:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "huggingface_hub is not installed. Run:\n"
            "  pip install -r requirements-ml.txt",
            file=sys.stderr,
        )
        return 1

    repo = settings.rife_weights_hf_repo
    filename = settings.rife_weights_hf_file
    revision = settings.rife_weights_hf_revision
    dest_dir = _model_dir()
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, filename)

    if os.path.exists(dest):
        print(f"RIFE weights already present at {dest} — nothing to do.")
        return 0

    print(f"Fetching {filename} from {repo}@{revision[:12]} ...")
    cached = hf_hub_download(repo_id=repo, filename=filename, revision=revision)
    shutil.copyfile(cached, dest)
    print(f"RIFE weights ready at {dest}")

    # Optional sanity check: confirm the arch loads the weights if torch is here.
    try:
        import torch

        from app.repo.rife_vendor.ifnet_hdv3 import IFNet

        net = IFNet()
        state = torch.load(dest, map_location="cpu", weights_only=False)
        if hasattr(state, "state_dict"):
            state = state.state_dict()
        state = {(k[7:] if k.startswith("module.") else k): v for k, v in state.items()}
        net.load_state_dict(state, strict=True)
        print("Verified: weights load into the vendored HDv3 arch (strict=True).")
    except ImportError:
        print("torch not installed — skipped the load-verification step.")
    except Exception as e:  # pragma: no cover - defensive
        print(f"WARNING: weights fetched but did NOT load cleanly: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
