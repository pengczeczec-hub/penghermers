from __future__ import annotations

import os
import subprocess
from typing import Any

_UTF8 = {"encoding": "utf-8", "errors": "replace"}


def utf8_env(env: dict[str, str] | None = None) -> dict[str, str]:
    out = (env or os.environ).copy()
    out.setdefault("PYTHONIOENCODING", "utf-8")
    return out


def run(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """subprocess.run，在 Windows 上以 UTF-8 讀取子行程輸出（避免 cp950 UnicodeDecodeError）。"""
    if kwargs.get("text") or kwargs.get("encoding") is not None:
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    if kwargs.get("capture_output") or kwargs.get("stdout") is subprocess.PIPE:
        kwargs["env"] = utf8_env(kwargs.get("env"))
    return subprocess.run(*popenargs, **kwargs)
