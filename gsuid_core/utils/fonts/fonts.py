from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Any

from PIL import ImageFont

_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def _find_font() -> str:
    for p in _CANDIDATES:
        if os.path.exists(p):
            return p
    # last resort: create nothing; matplotlib may still work with default
    return _CANDIDATES[-1]


# Upstream code does: font_manager.fontManager.addfont(str(FONT_ORIGIN_PATH))
# so this MUST be a real font file path.
FONT_ORIGIN_PATH = Path(_find_font())


@lru_cache(maxsize=32)
def core_font(size: int = 20) -> Any:
    try:
        if FONT_ORIGIN_PATH.exists():
            return ImageFont.truetype(str(FONT_ORIGIN_PATH), size=size)
    except Exception:
        pass
    return ImageFont.load_default()
