from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from rt916_spikefusionnet.model import DataEmbedding, TimesBlock, SpikeResidualBranch


class CalendarRegimeGate(nn.Module):
    def __init__(self, d_model, pred_len, dropout=0.1):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(d_model * 2 + 10, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, pred_len),
            nn.Sigmoid(),
        )

    def forward(self, base_context, spike_context, calendar_feats):
        gate_input = torch.cat([base_context, spike_context, calendar_feats], dim=-1)
        return self.gate(gate_input)


class AnnualSpikeGatedTimesNet(nn.Module):
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
        delta_scale=0.12,
        editable_horizon=(9, 16),
    ):
        super().__init__()
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.target_index = target_index
        self.known_target_len = known_target_len if known_target_len is not None else (seq_len - 2 * pred_len)
        self.delta_scale = float(delta_scale)
        self.editable_horizon = editable_horizon

        self.embedding = DataEmbedding(num_variates, d_model, dropout=dropout)
        self.blocks = nn.ModuleList(
            [TimesBlock(seq_len, pred_len, d_model, top_k=top_k, num_kernels=num_kernels) for _ in range(e_layers)]
        )
        self.norm = nn.LayerNorm(d_model)
        self.out_proj = nn.Linear(d_model, 1)

        self.hour_embed = nn.Embedding(25, 8)
        self.calendar_proj = nn.Sequential(
            nn.Linear(8 + 4 + 2 + 1, d_model),
            nn.GELU(),
            nn.Linear(d_model, 10),
        )
        self.spike_branch = SpikeResidualBranch(self.known_target_len, pred_len, d_model, dropout=dropout)
        self.dynamic_gate = CalendarRegimeGate(d_model, pred_len, dropout=dropout)

    def _calendar_features(self, x):
        bsz = x.size(0)
        hour_raw = torch.arange(1, self.pred_len + 1, device=x.device).unsqueeze(0).repeat(bsz, 1)
        hour_idx = hour_raw.long().clamp(1, 24)
        hour_emb = self.hour_embed(hour_idx)
        hour_sin = torch.sin(2 * math.pi * hour_raw / 24.0).unsqueeze(-1)
        hour_cos = torch.cos(2 * math.pi * hour_raw / 24.0).unsqueeze(-1)
        editable = ((hour_idx >= self.editable_horizon[0]) & (hour_idx <= self.editable_horizon[1])).float().unsqueeze(-1)
        hist_stats = torch.stack(
            [
                x.mean(dim=(1, 2)),
                x.std(dim=(1, 2)),
                x[:, -1, :].mean(dim=1),
                x[:, : self.known_target_len, self.target_index].std(dim=1),
            ],
            dim=-1,
        ).unsqueeze(1).repeat(1, self.pred_len, 1)
        feats = torch.cat([hour_emb, hist_stats, hour_sin, hour_cos, editable], dim=-1)
        return self.calendar_proj(feats).mean(dim=1), editable.squeeze(-1)

    def forward(self, x, anchor_pred=None):
        enc = self.embedding(x)
        for block in self.blocks:
            enc = self.norm(block(enc))

        future_tokens = enc[:, -self.pred_len :, :]
        base_pred = self.out_proj(future_tokens).squeeze(-1)
        base_context = future_tokens.mean(dim=1)

        target_hist = x[:, : self.known_target_len, self.target_index]
        spike_delta, spike_context = self.spike_branch(target_hist)
        spike_delta = self.delta_scale * torch.tanh(spike_delta)
        calendar_feats, editable_mask = self._calendar_features(x)
        gate = self.dynamic_gate(base_context, spike_context, calendar_feats)

        pred = base_pred + gate * spike_delta
        if anchor_pred is not None:
            anchor_pred = anchor_pred.to(pred.dtype)
            pred = editable_mask * pred + (1.0 - editable_mask) * anchor_pred
        pred = torch.clamp(pred, -0.35, 1.80)
        return pred

