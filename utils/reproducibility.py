"""全局随机种子与可复现性工具。

用法:
    from utils.reproducibility import set_global_seed
    set_global_seed(42, deterministic=True)
"""
from __future__ import annotations

import os
import random

import numpy as np


def set_global_seed(seed: int = 42, deterministic: bool = False) -> None:
    """Set project-level random seeds for reproducible model runs."""
    seed = int(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch
    except ImportError:
        return

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = bool(deterministic)

    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("highest")

    if hasattr(torch, "use_deterministic_algorithms"):
        torch.use_deterministic_algorithms(bool(deterministic), warn_only=True)
