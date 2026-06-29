from __future__ import annotations

import logging
from typing import Any

from sync_data import sync_dataset

logger = logging.getLogger(__name__)


def run_sync_dataset_pipeline(args: Any = None) -> dict:
    """Run the sync_dataset pipeline with optional CLI arguments.

    Parameters
    ----------
    args : argparse.Namespace or None
        If given, the following attributes are read:
          - sync_source (str): default "auto"
          - force_sync (bool): default False
          - require_fresh_data (bool): default False
          - date or start (str): target date for freshness check
          - data_path (str): custom data path
          - max_data_lag_hours (int): default 36
        When *args* is None, defaults are used (source=auto, no force).

    Returns
    -------
    dict — the sync manifest.
    """
    if args is None:
        return sync_dataset()

    source = getattr(args, "sync_source", "auto")
    force = getattr(args, "force_sync", False)
    require_fresh = getattr(args, "require_fresh_data", False)
    max_lag = getattr(args, "max_data_lag_hours", 36)

    # Determine target_date — prefer --date, then --start, then None
    target_date = getattr(args, "date", None)
    if target_date is None:
        target_date = getattr(args, "start", None)

    data_path = getattr(args, "data_path", None)

    logger.info(
        "sync_dataset: source=%s force=%s require_fresh=%s target=%s",
        source, force, require_fresh, target_date,
    )

    return sync_dataset(
        data_path=data_path,
        source=source,
        force=force,
        require_fresh=require_fresh,
        target_date=target_date,
        max_data_lag_hours=max_lag,
    )
