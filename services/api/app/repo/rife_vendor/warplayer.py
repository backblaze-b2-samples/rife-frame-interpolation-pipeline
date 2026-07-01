"""Backward optical-flow warp (vendored from Practical-RIFE, MIT).

Bilinear grid-sample warp used by the IFNet to warp each input frame toward the
target intermediate time using the estimated flow. torch is imported at module
load; this file is only imported lazily from rife_engine.py (never at API boot).
"""

import torch

_backwarp_grid: dict = {}


def warp(tenInput, tenFlow, device):
    k = (str(tenFlow.device), str(tenFlow.size()))
    if k not in _backwarp_grid:
        h = torch.linspace(-1.0, 1.0, tenFlow.shape[3], device=device).view(
            1, 1, 1, tenFlow.shape[3]
        ).expand(tenFlow.shape[0], -1, tenFlow.shape[2], -1)
        v = torch.linspace(-1.0, 1.0, tenFlow.shape[2], device=device).view(
            1, 1, tenFlow.shape[2], 1
        ).expand(tenFlow.shape[0], -1, -1, tenFlow.shape[3])
        _backwarp_grid[k] = torch.cat([h, v], 1).to(device)

    tenFlow = torch.cat(
        [
            tenFlow[:, 0:1, :, :] / ((tenInput.shape[3] - 1.0) / 2.0),
            tenFlow[:, 1:2, :, :] / ((tenInput.shape[2] - 1.0) / 2.0),
        ],
        1,
    )
    g = (_backwarp_grid[k] + tenFlow).permute(0, 2, 3, 1)
    return torch.nn.functional.grid_sample(
        input=tenInput, grid=g, mode="bilinear", padding_mode="border", align_corners=True
    )
