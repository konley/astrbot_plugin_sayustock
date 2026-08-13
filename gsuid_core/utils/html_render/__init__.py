from __future__ import annotations


async def render_md_to_bytes(md: str, **kwargs) -> bytes:
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (900, 1200), (255, 255, 255))
        d = ImageDraw.Draw(img)
        y = 20
        for line in (md or "").splitlines()[:60]:
            d.text((20, y), line[:80], fill=(0, 0, 0))
            y += 18
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return (md or "").encode("utf-8")
