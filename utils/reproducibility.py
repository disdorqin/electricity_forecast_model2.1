"""全局随机种子与可复现性工具。

用法:
    from utils.reproducibility import set_global_seed
    set_global_seed(42, deterministic=True)
"""
from __future__ import annotations

import os
import random
import warnings

import numpy as np


def set_global_seed(seed: int, deterministic: bool = False) -> None:
    """设置全局随机种子，覆盖 Python / NumPy / PyTorch / CUDA / cuDNN。

    Args:
        seed: 随机种子值 (int)。
        deterministic: 若为 True，强制 cuDNN 确定性算法并警告非确定性操作。
    """
    # 1) Python built-in
    random.seed(seed)

    # 2) NumPy
    np.random.seed(seed)

    # 3) PyTorch (optional)
    try:
        import torch
    except ImportError:
        torch = None  # type: ignore[assignment]

    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

        # cuDNN 确定性 / 基准
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = not deterministic

        # PyTorch 2.x+ 确定性算法
        if deterministic:
            torch.use_deterministic_algorithms(True, warn_only=True)
            # 在 CUDA >= 10.2 上减少非确定性
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    # 4) Python 哈希种子 (须在解释器启动时设定才有效, 此处仅记录)
    os.environ.setdefault("PYTHONHASHSEED", str(seed % (2**32)))

    # 5) 日志提示
    if deterministic:
        msg = (
            f"Global seed={seed}, deterministic=ON. "
            "cuDNN deterministic algorithms enabled; "
            "performance may be slower."
        )
    else:
        msg = f"Global seed={seed}, deterministic=OFF."

    # 在确定性模式下, 若某些操作仍是非确定的则静默处理
    if deterministic:
        warnings.filterwarnings("once", message=".*deterministic.*")
        warnings.warn(msg, stacklevel=2)
