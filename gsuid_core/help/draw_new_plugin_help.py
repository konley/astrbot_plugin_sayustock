from __future__ import annotations

from typing import Any


async def get_new_help(*args, **kwargs) -> bytes:
    # fallback empty png-ish
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (800, 400), (20, 24, 32))
        d = ImageDraw.Draw(img)
        d.text((40, 40), "SayuStock Help", fill=(240, 240, 240))
        d.text((40, 100), "发送 股票帮助 查看命令", fill=(180, 180, 180))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b""
