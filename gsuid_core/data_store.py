from __future__ import annotations

import os
from pathlib import Path

_BASE: Path | None = None


def set_res_base(path: str | Path) -> None:
    global _BASE
    _BASE = Path(path)
    _BASE.mkdir(parents=True, exist_ok=True)


def get_res_path() -> Path:
    global _BASE
    if _BASE is None:
        # fallback
        env = os.environ.get("SAYUSTOCK_DATA")
        if env:
            _BASE = Path(env)
        else:
            _BASE = Path(__file__).resolve().parents[2] / "data"
        _BASE.mkdir(parents=True, exist_ok=True)
    return _BASE
