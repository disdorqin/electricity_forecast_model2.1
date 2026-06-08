from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from rt916_spikefusionnet.model import DataEmbedding, TimesBlock


class MovingAverage(nn.Module):
    def __init__(self, kernel_size: int):
        super().__init__()
        self.kernel_size = int(kernel_size)
        self.avg = nn.AvgPool1d(kernel_size=self.kernel_size, stride=1)

    def forward(self, x):
        if self.kernel_size <= 1:
            return x
        pad_left = (self.kernel_size - 1) // 2
        pad_right = self.kernel_size - 1 - pad_left
        x_pad = F.pad(x.unsqueeze(1), (pad_left, pad_right), mode="replicate").squeeze(1)
        return self.avg(x_pad.unsqueeze(1)).squeeze(1)


class SeriesDecomposition(nn.Module):
    def __init__(self, kernel_size: int):
        super().__init__()
        self.moving_avg = MovingAverage(kernel_size)

    def forward(self, x):
        trend = self.moving_avg(x)
        seasonal = x - trend
        return seasonal, trend


class MultiScaleMixHead(nn.Module):
    def __init__(self, d_model: int, pred_len: int, dropout: float = 0.1):
        super().__init__()
        self.pred_len = int(pred_len)
        self.scale_weights = nn.Parameter(torch.tensor([0.45, 0.35, 0.20], dtype=torch.float32))
        self.trend_proj = nn.Sequential(
            nn.Linear(pred_len * 3, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, pred_len),
        )
        self.season_proj = nn.Sequential(
            nn.Linear(pred_len * 3, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, pred_len),
        )

    def _extract_scale(self, x, step: int):
        if x.size(1) < step * self.pred_len:
            step = max(1, x.size(1) // self.pred_len)
        hist = x[:, -step * self.pred_len :]
        hist = hist.reshape(x.size(0), self.pred_len, step).mean(dim=-1)
        return hist

    def forward(self, seasonal_hist, trend_hist):
        season_feats = [self._extract_scale(seasonal_hist, s) for s in (1, 2, 4)]
        trend_feats = [self._extract_scale(trend_hist, s) for s in (1, 2, 4)]
        season_stack = torch.cat(season_feats, dim=-1)
        trend_stack = torch.cat(trend_feats, dim=-1)
        weights = torch.softmax(self.scale_weights, dim=0)
        trend_mix = self.trend_proj(trend_stack)
        season_mix = self.season_proj(season_stack)
        return weights[0] * trend_feats[0] + weights[1] * trend_feats[1] + weights[2] * trend_feats[2] + 0.35 * trend_mix + 0.20 * season_mix


class DayAheadTimeMixerNet(nn.Module):
    def __init__(
        self,
        num_variates,
        seq_len,
        pred_len,
        d_model=128,
        e_layers=2,
        top_k=3,
        num_kernels=6,
        dropout=0.1,
        target_index=-1,
        known_target_len=None,
        delta_scale=0.08,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.target_index = target_index
        self.known_target_len = known_target_len if known_target_len is not None else (seq_len - pred_len)
        self.delta_scale = float(delta_scale)

        self.embedding = DataEmbedding(num_variates, d_model, dropout=dropout)
        self.blocks = nn.ModuleList(
            [TimesBlock(seq_len, pred_len, d_model, top_k=top_k, num_kernels=num_kernels) for _ in range(e_layers)]
        )
        self.norm = nn.LayerNorm(d_model)
        self.out_proj = nn.Linear(d_model, 1)
        self.decomp = SeriesDecomposition(kernel_size=5)
        self.mix_head = MultiScaleMixHead(d_model, pred_len, dropout=dropout)
        self.future_gate = nn.Sequential(
            nn.Linear(d_model + 4, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, pred_len),
            nn.Sigmoid(),
        )

    def forward(self, x, anchor_pred=None):
        enc = self.embedding(x)
        for block in self.blocks:
            enc = self.norm(block(enc))

        future_tokens = enc[:, -self.pred_len :, :]
        base_pred = self.out_proj(future_tokens).squeeze(-1)
        base_context = future_tokens.mean(dim=1)

        target_hist = x[:, : self.known_target_len, self.target_index]
        seasonal_hist, trend_hist = self.decomp(target_hist)
        mixed_anchor = self.mix_head(seasonal_hist, trend_hist)

        future_known = x[:, -self.pred_len :, :]
        future_stats = torch.stack(
            [
                future_known.mean(dim=(1, 2)),
                future_known.std(dim=(1, 2)),
                future_known[:, :, self.target_index].mean(dim=1),
                future_known[:, :, self.target_index].std(dim=1),
            ],
            dim=-1,
        )
        gate = self.future_gate(torch.cat([base_context, future_stats], dim=-1))

        pred = (1.0 - gate) * base_pred + gate * mixed_anchor
        if anchor_pred is not None:
            anchor_pred = anchor_pred.to(pred.dtype)
            pred = 0.75 * pred + 0.25 * anchor_pred
        pred = torch.clamp(pred, -0.35, 1.80)
        return pred

