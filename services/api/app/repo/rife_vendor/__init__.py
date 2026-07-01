"""Vendored Practical-RIFE HDv3 model architecture.

This package contains the RIFE (Real-Time Intermediate Flow Estimation) HDv3
network architecture, vendored from the MIT-licensed upstream project by
hzwer (Zhewei Huang) — https://github.com/hzwer/Practical-RIFE.

Only the model ARCHITECTURE lives here (pure torch nn.Module code). The trained
weights (`flownet.pkl`) are NOT committed — they are fetched at setup time by
scripts/setup_rife.py from a pinned HuggingFace mirror into the (gitignored)
RIFE_MODEL_DIR. See LICENSE and NOTICE in this directory for attribution.

The architecture here is the HDv3 IFNet (three IFBlocks + a soft-mask blend of
two optical-flow-warped frames). It has been verified to load the pinned
default weights with `strict=True` and to produce a valid interpolated frame on
CPU.
"""
