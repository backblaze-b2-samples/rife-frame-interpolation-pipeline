"""RIFE HDv3 IFNet — intermediate-flow frame interpolation network.

Vendored from the MIT-licensed Practical-RIFE project by hzwer (Zhewei Huang).
See LICENSE and NOTICE in this directory. This is the HDv3 variant whose
state-dict exactly matches the pinned default weights (`flownet.pkl`, 160
tensors) fetched by scripts/setup_rife.py — verified to load with strict=True
and to produce a valid interpolated frame on CPU.

Given two frames, `IFNet.forward` estimates a bidirectional optical flow at
three progressively finer scales, backward-warps each frame toward the target
midpoint, and blends the two warped frames with a learned soft mask — genuine
neural interpolation, not a pixel average.

torch is imported at load; this module is only imported lazily from
app/repo/rife_engine.py, never at API boot.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from app.repo.rife_vendor.warplayer import warp


def conv(in_planes, out_planes, kernel_size=3, stride=1, padding=1, dilation=1):
    return nn.Sequential(
        nn.Conv2d(
            in_planes, out_planes, kernel_size=kernel_size, stride=stride,
            padding=padding, dilation=dilation, bias=True,
        ),
        nn.PReLU(out_planes),
    )


class IFBlock(nn.Module):
    """One intermediate-flow block: downsample -> residual convs -> flow+mask."""

    def __init__(self, in_planes, c=90):
        super().__init__()
        self.conv0 = nn.Sequential(
            conv(in_planes, c // 2, 3, 2, 1),
            conv(c // 2, c, 3, 2, 1),
        )
        self.convblock0 = nn.Sequential(conv(c, c), conv(c, c))
        self.convblock1 = nn.Sequential(conv(c, c), conv(c, c))
        self.convblock2 = nn.Sequential(conv(c, c), conv(c, c))
        self.convblock3 = nn.Sequential(conv(c, c), conv(c, c))
        self.conv1 = nn.Sequential(
            nn.ConvTranspose2d(c, c // 2, 4, 2, 1),
            nn.PReLU(c // 2),
            nn.ConvTranspose2d(c // 2, 4, 4, 2, 1),
        )
        self.conv2 = nn.Sequential(
            nn.ConvTranspose2d(c, c // 2, 4, 2, 1),
            nn.PReLU(c // 2),
            nn.ConvTranspose2d(c // 2, 1, 4, 2, 1),
        )

    def forward(self, x, flow, scale=1):
        x = F.interpolate(
            x, scale_factor=1.0 / scale, mode="bilinear",
            align_corners=False, recompute_scale_factor=False,
        )
        flow = F.interpolate(
            flow, scale_factor=1.0 / scale, mode="bilinear",
            align_corners=False, recompute_scale_factor=False,
        ) * (1.0 / scale)
        feat = self.conv0(torch.cat((x, flow), 1))
        feat = self.convblock0(feat) + feat
        feat = self.convblock1(feat) + feat
        feat = self.convblock2(feat) + feat
        feat = self.convblock3(feat) + feat
        flow = self.conv1(feat)
        mask = self.conv2(feat)
        flow = F.interpolate(
            flow, scale_factor=scale, mode="bilinear",
            align_corners=False, recompute_scale_factor=False,
        ) * scale
        mask = F.interpolate(
            mask, scale_factor=scale, mode="bilinear",
            align_corners=False, recompute_scale_factor=False,
        )
        return flow, mask


class IFNet(nn.Module):
    """Three-scale intermediate-flow network producing one midpoint frame."""

    def __init__(self):
        super().__init__()
        self.block0 = IFBlock(7 + 4, c=90)
        self.block1 = IFBlock(7 + 4, c=90)
        self.block2 = IFBlock(7 + 4, c=90)
        # Teacher block — present in the checkpoint but unused at inference.
        self.block_tea = IFBlock(10 + 4, c=90)

    def forward(self, x, scale_list=(4, 2, 1)):
        img0 = x[:, :3]
        img1 = x[:, 3:6]
        flow = torch.zeros_like(x[:, :4])
        mask = torch.zeros_like(x[:, :1])
        warped0, warped1 = img0, img1
        for i, block in enumerate((self.block0, self.block1, self.block2)):
            f, m = block(torch.cat((img0, img1, mask), 1), flow, scale=scale_list[i])
            flow = flow + f
            mask = mask + m
            warped0 = warp(img0, flow[:, :2], x.device)
            warped1 = warp(img1, flow[:, 2:4], x.device)
        mask = torch.sigmoid(mask)
        merged = warped0 * mask + warped1 * (1 - mask)
        return flow, mask, merged
