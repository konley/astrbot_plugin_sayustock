from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Union


async def convert_img(img: Any) -> Union[bytes, str]:
    """Convert PIL Image / path / bytes to PNG bytes for bot.send."""
    if img is None:
        return b""
    if isinstance(img, (bytes, bytearray)):
        return bytes(img)
    if isinstance(img, str):
        p = Path(img)
        if p.exists():
            return p.read_bytes()
        return img  # error text
    if isinstance(img, Path):
        return img.read_bytes() if img.exists() else str(img)
    # PIL Image
    if hasattr(img, "save"):
        buf = BytesIO()
        # ensure RGB/RGBA
        try:
            img.save(buf, format="PNG")
        except Exception:
            rgb = img.convert("RGBA") if hasattr(img, "convert") else img
            buf = BytesIO()
            rgb.save(buf, format="PNG")
        return buf.getvalue()
    return str(img).encode("utf-8")
