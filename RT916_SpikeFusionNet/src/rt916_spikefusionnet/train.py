import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rt916_spikefusionnet.core import run


if __name__ == "__main__":
    run(
        target="实时电价",
        start_end_list=["2026-02-01 01:00:00", "2026-02-10 00:00:00"],
        mod="all",
    )

