"""Console entry: hermes-main"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(root / "hermes_main.py"), run_name="__main__")
