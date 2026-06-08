from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class AnnualProtectedCappedLoss(nn.Module):
    def __init__(
        self,
        low_thr,
        high_thr,
        alpha=1.0,
        diff_alpha=0.25,
        huber_beta=0.05,
        mse_gamma=0.2,
        protected_weight=1.5,
        editable_horizon=(9, 16),
    ):
        super().__init__()
        self.low_thr = float(low_thr)
        self.high_thr = float(high_thr)
        self.alpha = float(alpha)
        self.diff_alpha = float(diff_alpha)
        self.huber_beta = float(huber_beta)
        self.mse_gamma = float(mse_gamma)
        self.protected_weight = float(protected_weight)
        self.editable_horizon = editable_horizon

    def forward(self, pred, target):
        err = pred - target
        tail_mask = ((target <= self.low_thr) | (target >= self.high_thr)).float()
        tail_weight = 1.0 + self.alpha * tail_mask
        diff = torch.zeros_like(target)
        if target.size(1) > 1:
            diff[:, 1:] = torch.abs(target[:, 1:] - target[:, :-1])
        diff_scale = diff / (diff.mean(dim=1, keepdim=True) + 1e-6)
        weight = tail_weight + self.diff_alpha * diff_scale.detach()
        huber = F.smooth_l1_loss(pred, target, reduction="none", beta=self.huber_beta)
        mse = err.square()
        base = (weight * huber).mean() + self.mse_gamma * (weight * mse).mean()

        h = target.size(1)
        editable = torch.zeros_like(target)
        lo, hi = self.editable_horizon
        lo = max(1, int(lo)) - 1
        hi = min(h, int(hi))
        editable[:, lo:hi] = 1.0
        protected = 1.0 - editable
        protected_penalty = (protected * err.square()).mean()
        return base + self.protected_weight * protected_penalty

