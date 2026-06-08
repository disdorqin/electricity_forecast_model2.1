"""Release-safe RT916 SpikeFusionNet package."""

from .annual_loss import AnnualProtectedCappedLoss
from .annual_model import AnnualSpikeGatedTimesNet
from .core import run, run_daily_asof_backtest, run_joint_da_rt_daily_backtest, train_interface

__all__ = [
    "AnnualProtectedCappedLoss",
    "AnnualSpikeGatedTimesNet",
    "run",
    "run_daily_asof_backtest",
    "run_joint_da_rt_daily_backtest",
    "train_interface",
]

__version__ = "1.0.0-release-safe"
